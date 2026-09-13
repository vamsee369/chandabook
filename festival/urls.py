from django.urls import path
from . import views
from accounts import views as accounts_views

urlpatterns = [
    path("", views.home, name="home"),
    path("festivals/", views.festival_list, name="festival_list"),
    path("festivals/create/", views.create_festival, name="create_festival"),
    path("festivals/<int:fid>/", views.festival_dashboard, name="festival_dashboard"),
    path("festivals/<int:fid>/edit/", views.edit_festival, name="edit_festival"),
    path("festivals/<int:fid>/delete/", views.delete_festival, name="delete_festival"),

    # Members
    path("festivals/<int:fid>/members/", views.manage_members, name="manage_members"),
    path("festivals/<int:fid>/members/<int:mid>/edit/", views.edit_member, name="edit_member"),
    path("festivals/<int:fid>/members/<int:mid>/delete/", views.delete_member, name="delete_member"),

    # Collections (Chanda)
    path("festivals/<int:fid>/collections/", views.view_collections, name="view_collections"),
    path("festivals/<int:fid>/collections/add/", views.add_collection, name="add_collection"),
    path("festivals/<int:fid>/collections/<int:cid>/delete/", views.delete_collection, name="delete_collection"),

    # Expenses
    path("festivals/<int:fid>/expenses/", views.view_expenses, name="view_expenses"),
    path("festivals/<int:fid>/expenses/add/", views.add_expense, name="add_expense"),
    path("festivals/<int:fid>/expenses/<int:eid>/delete/", views.delete_expense, name="delete_expense"),

    # Reports & Exports
    path("festivals/<int:fid>/member-report/", views.member_report, name="member_report"),
    path("festivals/<int:fid>/export/", views.export_summary, name="export_summary"),
    path("festivals/<int:fid>/export-pdf/", views.export_pdf, name="export_pdf"),
    path("festivals/<int:fid>/ocr-receipt/", views.ocr_receipt, name="ocr_receipt"),

    # Auth
    path("login/", accounts_views.login_view, name="login"),
]
