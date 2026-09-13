from decimal import Decimal
from collections import defaultdict
from datetime import date
import re
import io
import os

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.template.loader import render_to_string

# ── pytesseract (optional – gracefully disabled if not installed) ──────────────
try:
    import pytesseract
    from PIL import Image as PILImage
    _TESSERACT_PATH = os.environ.get("TESSERACT_PATH", "")
    if _TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .models import Festival, ChandaMember, ChandaCollection, FestivalExpense


# ─── helpers ──────────────────────────────────────────────────────────────────

def _visible(user):
    if not user.is_authenticated:
        return Festival.objects.none()
    if user.is_superuser:
        return Festival.objects.all()
    return Festival.objects.filter(created_by=user)


# ─── Home ──────────────────────────────────────────────────────────────────────

def home(request):
    ongoing, upcoming, recent = [], [], []
    if request.user.is_authenticated:
        festivals = _visible(request.user)
        today = date.today()
        ongoing  = list(festivals.filter(start_date__lte=today, end_date__gte=today).order_by("start_date"))
        upcoming = list(festivals.filter(start_date__gt=today).order_by("start_date")[:5])
        recent   = list(festivals.order_by("-created_at")[:6])
    return render(request, "festival/home.html", {
        "ongoing": ongoing, "upcoming": upcoming, "recent": recent,
    })


# ─── Festival CRUD ────────────────────────────────────────────────────────────

@login_required
def create_festival(request):
    if request.method == "POST":
        Festival.objects.create(
            name=request.POST["name"],
            festival_type=request.POST["festival_type"],
            location=request.POST["location"],
            start_date=request.POST["start_date"],
            end_date=request.POST["end_date"],
            target_collection=request.POST.get("target_collection") or 0,
            description=request.POST.get("description", ""),
            created_by=request.user,
        )
        messages.success(request, "Festival created successfully!")
        return redirect("festival_list")
    from .models import FESTIVAL_TYPES
    return render(request, "festival/create_festival.html", {"festival_types": FESTIVAL_TYPES})


@login_required
def edit_festival(request, fid):
    festival = get_object_or_404(Festival, id=fid, created_by=request.user)
    if request.method == "POST":
        festival.name = request.POST["name"]
        festival.festival_type = request.POST["festival_type"]
        festival.location = request.POST["location"]
        festival.start_date = request.POST["start_date"]
        festival.end_date = request.POST["end_date"]
        festival.target_collection = request.POST.get("target_collection") or 0
        festival.description = request.POST.get("description", "")
        festival.save()
        messages.success(request, "Festival updated!")
        return redirect("festival_dashboard", fid=festival.id)
    from .models import FESTIVAL_TYPES
    return render(request, "festival/edit_festival.html", {
        "festival": festival, "festival_types": FESTIVAL_TYPES,
    })


@login_required
def delete_festival(request, fid):
    festival = get_object_or_404(Festival, id=fid, created_by=request.user)
    if request.method == "POST":
        festival.delete()
        messages.success(request, "Festival deleted.")
        return redirect("festival_list")
    return render(request, "festival/confirm_delete.html", {"festival": festival})


@login_required
def festival_list(request):
    festivals = _visible(request.user).order_by("-created_at")
    return render(request, "festival/festival_list.html", {"festivals": festivals})


# ─── Festival Dashboard ───────────────────────────────────────────────────────

@login_required
def festival_dashboard(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    if not (request.user.is_superuser or festival.created_by == request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    members     = festival.members.all()
    collections = festival.collections.select_related("member").order_by("-date_collected")[:10]
    expenses    = festival.expenses.order_by("-date")[:10]

    total_collected = festival.total_collected
    total_expenses  = festival.total_expenses
    balance         = festival.balance
    target          = festival.target_collection
    upi_balance     = festival.upi_balance
    cash_balance    = festival.cash_balance
    upi_collected   = festival.upi_collected
    cash_collected  = festival.cash_collected
    upi_expenses    = festival.upi_expenses
    cash_expenses   = festival.cash_expenses

    # category breakdown for expenses
    exp_by_cat = (
        festival.expenses.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    # payment mode breakdown for collections
    coll_by_mode = (
        festival.collections.values("payment_mode")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    # member summary
    members_paid   = sum(1 for m in members if m.is_fully_paid)
    members_pending = members.count() - members_paid
    total_promised  = members.aggregate(t=Sum("promised_amount"))["t"] or Decimal("0")

    # daily collection for sparkline (last 30 days)
    daily = defaultdict(float)
    for c in festival.collections.all():
        daily[str(c.date_collected)] += float(c.amount)

    return render(request, "festival/festival_dashboard.html", {
        "festival": festival,
        "members": members,
        "collections": collections,
        "expenses": expenses,
        "total_collected": total_collected,
        "total_expenses": total_expenses,
        "balance": balance,
        "target": target,
        "collection_pct": festival.collection_pct,
        "exp_by_cat": exp_by_cat,
        "coll_by_mode": coll_by_mode,
        "members_paid": members_paid,
        "members_pending": members_pending,
        "total_promised": total_promised,
        "daily_json": dict(daily),
        "upi_balance": upi_balance,
        "cash_balance": cash_balance,
        "upi_collected": upi_collected,
        "cash_collected": cash_collected,
        "upi_expenses": upi_expenses,
        "cash_expenses": cash_expenses,
    })


# ─── Members ──────────────────────────────────────────────────────────────────

@login_required
def manage_members(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    if request.method == "POST":
        ChandaMember.objects.create(
            festival=festival,
            name=request.POST["name"],
            phone=request.POST.get("phone", ""),
            address=request.POST.get("address", ""),
            promised_amount=request.POST.get("promised_amount") or 0,
            notes=request.POST.get("notes", ""),
        )
        messages.success(request, "Member added!")
        return redirect("manage_members", fid=fid)
    members = festival.members.all()
    return render(request, "festival/manage_members.html", {
        "festival": festival, "members": members,
    })


@login_required
def edit_member(request, fid, mid):
    festival = get_object_or_404(Festival, id=fid)
    member   = get_object_or_404(ChandaMember, id=mid, festival=festival)
    if request.method == "POST":
        member.name = request.POST["name"]
        member.phone = request.POST.get("phone", "")
        member.address = request.POST.get("address", "")
        member.promised_amount = request.POST.get("promised_amount") or 0
        member.notes = request.POST.get("notes", "")
        member.save()
        messages.success(request, "Member updated!")
        return redirect("manage_members", fid=fid)
    return render(request, "festival/edit_member.html", {
        "festival": festival, "member": member,
    })


@login_required
def delete_member(request, fid, mid):
    festival = get_object_or_404(Festival, id=fid)
    member   = get_object_or_404(ChandaMember, id=mid, festival=festival)
    if request.method == "POST":
        member.delete()
        messages.success(request, "Member removed.")
        return redirect("manage_members", fid=fid)
    return render(request, "festival/confirm_delete_member.html", {
        "festival": festival, "member": member,
    })


# ─── Chanda Collections ───────────────────────────────────────────────────────

@login_required
def add_collection(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    members = festival.members.all()
    if request.method == "POST":
        member_id = request.POST.get("member_id")
        member = ChandaMember.objects.get(id=member_id) if member_id else None
        donor_name = request.POST.get("donor_name", "").strip()
        if member and not donor_name:
            donor_name = member.name
        ChandaCollection.objects.create(
            festival=festival,
            member=member,
            donor_name=donor_name or (member.name if member else "Anonymous"),
            amount=request.POST["amount"],
            payment_mode=request.POST.get("payment_mode", "Cash"),
            collected_by=request.POST.get("collected_by", ""),
            date_collected=request.POST.get("date_collected") or date.today(),
            receipt_no=request.POST.get("receipt_no", ""),
            notes=request.POST.get("notes", ""),
        )
        messages.success(request, "Chanda recorded successfully!")
        return redirect("view_collections", fid=fid)
    from .models import PAYMENT_CHOICES
    return render(request, "festival/add_collection.html", {
        "festival": festival,
        "members": members,
        "payment_choices": PAYMENT_CHOICES,
        "today": date.today(),
    })


@login_required
def view_collections(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    qs = festival.collections.select_related("member").order_by("-date_collected")

    # filters
    mode   = request.GET.get("mode", "")
    member = request.GET.get("member", "")
    q      = request.GET.get("q", "")
    if mode:
        qs = qs.filter(payment_mode=mode)
    if member:
        qs = qs.filter(Q(donor_name__icontains=member) | Q(member__name__icontains=member))
    if q:
        qs = qs.filter(Q(donor_name__icontains=q) | Q(notes__icontains=q) | Q(receipt_no__icontains=q))

    total = qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")
    from .models import PAYMENT_CHOICES
    return render(request, "festival/view_collections.html", {
        "festival": festival,
        "collections": qs,
        "total": total,
        "payment_choices": PAYMENT_CHOICES,
        "filter_mode": mode,
        "filter_member": member,
        "filter_q": q,
    })


@login_required
def delete_collection(request, fid, cid):
    festival   = get_object_or_404(Festival, id=fid)
    collection = get_object_or_404(ChandaCollection, id=cid, festival=festival)
    if request.method == "POST":
        collection.delete()
        messages.success(request, "Collection entry deleted.")
    return redirect("view_collections", fid=fid)


# ─── Expenses ─────────────────────────────────────────────────────────────────

@login_required
def add_expense(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    if request.method == "POST":
        exp = FestivalExpense(
            festival=festival,
            title=request.POST["title"],
            amount=request.POST["amount"],
            paid_by=request.POST.get("paid_by", ""),
            payment_mode=request.POST.get("payment_mode", "Cash"),
            category=request.POST.get("category", "Miscellaneous"),
            date=request.POST.get("date") or date.today(),
            description=request.POST.get("description", ""),
        )
        if request.FILES.get("receipt"):
            exp.receipt = request.FILES["receipt"]
        exp.save()
        messages.success(request, "Expense recorded!")
        return redirect("view_expenses", fid=fid)
    from .models import PAYMENT_CHOICES
    return render(request, "festival/add_expense.html", {
        "festival": festival,
        "categories": FestivalExpense.CATEGORY_CHOICES,
        "payment_choices": PAYMENT_CHOICES,
        "today": date.today(),
    })


@login_required
def view_expenses(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    qs = festival.expenses.order_by("-date")

    cat = request.GET.get("cat", "")
    q   = request.GET.get("q", "")
    if cat:
        qs = qs.filter(category=cat)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(paid_by__icontains=q))

    total = qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")
    return render(request, "festival/view_expenses.html", {
        "festival": festival,
        "expenses": qs,
        "total": total,
        "categories": FestivalExpense.CATEGORY_CHOICES,
        "filter_cat": cat,
        "filter_q": q,
    })


@login_required
def delete_expense(request, fid, eid):
    festival = get_object_or_404(Festival, id=fid)
    expense  = get_object_or_404(FestivalExpense, id=eid, festival=festival)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
    return redirect("view_expenses", fid=fid)


# ─── Member-wise Report ───────────────────────────────────────────────────────

@login_required
def member_report(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    members  = festival.members.prefetch_related("collections").all()
    rows = []
    for m in members:
        rows.append({
            "member": m,
            "paid": m.total_paid,
            "pending": m.pending_amount,
            "paid_fully": m.is_fully_paid,
            "collections": m.collections.order_by("-date_collected"),
        })
    return render(request, "festival/member_report.html", {
        "festival": festival, "rows": rows,
    })


# ─── Export simple summary ────────────────────────────────────────────────────

@login_required
def export_summary(request, fid):
    festival = get_object_or_404(Festival, id=fid)
    lines = [
        f"Festival: {festival.name}",
        f"Type: {festival.festival_type}",
        f"Location: {festival.location}",
        f"Dates: {festival.start_date} to {festival.end_date}",
        f"Target Collection: ₹{festival.target_collection}",
        f"",
        f"=== CHANDA COLLECTIONS ===",
        f"{'Date':<12} {'Donor':<25} {'Mode':<12} {'Amount':>10} {'Collected By':<20} {'Receipt No'}",
        "-" * 90,
    ]
    total_coll = Decimal("0")
    for c in festival.collections.order_by("date_collected"):
        lines.append(
            f"{str(c.date_collected):<12} {c.donor_name:<25} {c.payment_mode:<12} ₹{c.amount:>9} {c.collected_by:<20} {c.receipt_no}"
        )
        total_coll += c.amount
    lines += [f"", f"TOTAL COLLECTIONS: ₹{total_coll}", f""]

    lines += [
        f"=== FESTIVAL EXPENSES ===",
        f"{'Date':<12} {'Title':<30} {'Category':<22} {'Paid By':<20} {'Amount':>10}",
        "-" * 100,
    ]
    total_exp = Decimal("0")
    for e in festival.expenses.order_by("date"):
        lines.append(
            f"{str(e.date):<12} {e.title:<30} {e.category:<22} {e.paid_by:<20} ₹{e.amount:>9}"
        )
        total_exp += e.amount
    lines += [
        f"",
        f"TOTAL EXPENSES : ₹{total_exp}",
        f"BALANCE        : ₹{total_coll - total_exp}",
    ]

    response = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="chanda_summary_{festival.id}.txt"'
    )
    return response


# ─── OCR Receipt ──────────────────────────────────────────────────────────────

@login_required
def ocr_receipt(request, fid):
    """POST a receipt image → JSON with extracted amount, merchant, notes."""
    festival = get_object_or_404(Festival, id=fid)

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    if not TESSERACT_AVAILABLE:
        return JsonResponse({"error": "pytesseract is not installed on this server."}, status=500)

    image_file = request.FILES.get("receipt")
    if not image_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    try:
        img = PILImage.open(io.BytesIO(image_file.read()))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        raw_text = pytesseract.image_to_string(img)

        # ── Extract total amount ──────────────────────────────────────────────
        amount = None
        for pat in [
            r'(?:total|grand\s*total|amount\s*due|net\s*amount|subtotal)[^\d]*([\d,]+\.?\d*)',
            r'[₹Rs\.]+\s*([\d,]+\.?\d*)',
            r'([\d,]+\.\d{2})\s*(?:INR|Rs|₹)?',
        ]:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                amount = m.group(1).replace(",", "")
                break

        # ── Extract GST / tax ─────────────────────────────────────────────────
        gst = None
        for pat in [
            r'(?:gst|cgst\s*\+\s*sgst|igst|tax)[^\d]*([\d,]+\.?\d*)',
            r'(?:cgst|sgst)[^\d]*([\d,]+\.?\d*)',
        ]:
            matches = re.findall(pat, raw_text, re.IGNORECASE)
            if matches:
                gst = str(round(sum(float(x.replace(",", "")) for x in matches), 2))
                break

        # ── Extract vendor / merchant name (first meaningful line) ────────────
        merchant = None
        skip_words = {"invoice", "receipt", "bill", "tax", "gst", "date", "time",
                      "cash", "memo", "voucher", "payment"}
        lines = [l.strip() for l in raw_text.splitlines() if len(l.strip()) > 3]
        for line in lines[:6]:
            clean = line.strip()
            if not re.match(r'^[\d\s\-\/\.:,#]+$', clean) and clean.lower() not in skip_words:
                merchant = clean[:120]
                break

        return JsonResponse({
            "amount":   amount or "",
            "gst":      gst or "",
            "merchant": merchant or "",
            "raw_text": raw_text[:600],
        })

    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


# ─── PDF Export ───────────────────────────────────────────────────────────────

@login_required
def export_pdf(request, fid):
    """Generate a beautiful A4 PDF summary for the festival."""
    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError:
        return HttpResponse(
            "WeasyPrint is not installed. Run: pip install weasyprint",
            status=500,
            content_type="text/plain",
        )

    festival    = get_object_or_404(Festival, id=fid)
    collections = festival.collections.select_related("member").order_by("date_collected")
    expenses    = festival.expenses.order_by("date")

    total_collected = festival.total_collected
    total_expenses  = festival.total_expenses
    balance         = festival.balance

    # category breakdown
    from django.db.models import Sum as DSum
    exp_by_cat = list(
        festival.expenses.values("category")
        .annotate(total=DSum("amount"))
        .order_by("-total")
    )

    # payment mode breakdown for collections
    coll_by_mode = list(
        festival.collections.values("payment_mode")
        .annotate(total=DSum("amount"))
        .order_by("-total")
    )

    # member summary
    members = list(festival.members.all())
    members_data = []
    for m in members:
        members_data.append({
            "name":     m.name,
            "phone":    m.phone,
            "promised": m.promised_amount,
            "paid":     m.total_paid,
            "pending":  m.pending_amount,
            "status":   "Paid" if m.is_fully_paid else "Pending",
        })

    html_string = render_to_string("festival/export_pdf.html", {
        "festival":        festival,
        "collections":     collections,
        "expenses":        expenses,
        "total_collected": total_collected,
        "total_expenses":  total_expenses,
        "balance":         balance,
        "exp_by_cat":      exp_by_cat,
        "coll_by_mode":    coll_by_mode,
        "members_data":    members_data,
        "collection_pct":  festival.collection_pct,
        "export_date":     date.today(),
    })

    pdf_bytes = io.BytesIO()
    WeasyprintHTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)

    safe_name = re.sub(r'[^\w\-]', '_', festival.name)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}_chanda_report.pdf"'
    return response
