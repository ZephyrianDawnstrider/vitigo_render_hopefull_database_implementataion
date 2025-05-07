from django.urls import path
from .views import (
    AccessControlDashboardView, 
    CreateRoleView,
    RoleDetailView,
    EditRoleView, 
    DeleteRoleView,
    ModuleListView,
    ManageRolesView,
    BulkUpdateView,
    ExportDataView,
    RolePermissionsView,
)

urlpatterns = [
    path('dashboard/', AccessControlDashboardView.as_view(), name='access_control_dashboard'),
    path('roles/create/', CreateRoleView.as_view(), name='create_role'),
    path('role/<int:role_id>/', RoleDetailView.as_view(), name='role_detail'),
    path('role/<int:role_id>/edit/', EditRoleView.as_view(), name='edit_role'),
    path('role/<int:role_id>/delete/', DeleteRoleView.as_view(), name='delete_role'),
    path('modules/', ModuleListView.as_view(), name='module_list'),
    path('roles/manage/', ManageRolesView.as_view(), name='manage_roles'),
    path('roles/bulk-update/', BulkUpdateView.as_view(), name='bulk_update'),
    path('export/', ExportDataView.as_view(), name='export_data'),
    path('roles/<int:role_id>/permissions/', RolePermissionsView.as_view(), name='role_permissions'),
]
