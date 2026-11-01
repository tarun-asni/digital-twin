from django.core.management.base import BaseCommand
from sensegrid.config import API_ENDPOINTS
from user_authentication.models import Role, Permission, APIEndpoint

class Command(BaseCommand):
    help = 'Create admin role with full_access permission for explicitly defined endpoints'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Loading endpoints from api_config.py...")

        all_endpoints = []
        for url_name, method, description in API_ENDPOINTS:
            # Generate clean name (e.g., 'get_trigger_detection')
            clean_name = f"{method.lower()}_{url_name.replace('-', '_')}"

            # Create or get APIEndpoint
            endpoint, created = APIEndpoint.objects.get_or_create(
                name=clean_name,
                defaults={
                    'path': f'/{url_name}/',
                    'method': method.upper()
                }
            )
            if created:
                self.stdout.write(f"  ➕ Created: {clean_name} ({method})")
            all_endpoints.append(endpoint)

        # Create full_access permission
        full_access, _ = Permission.objects.get_or_create(
            name='full_access',
            defaults={'description': 'Full access to all defined endpoints'}
        )
        full_access.api_endpoints.set(all_endpoints)
        
        self.create_operator(all_endpoints)

        # Assign to admin
        admin_role, _ = Role.objects.get_or_create(name='admin')
        admin_role.permissions.set([full_access])

        self.stdout.write(
            self.style.SUCCESS(f"✅ Setup complete! Admin role has 'full_access' covering {len(all_endpoints)} endpoints.")
        )
        
    def create_operator(self, endpoints: list['APIEndpoint']):
        """
        Creates or updates the 'operator' Role and assigns it a 
        'view_access' Permission covering specific endpoints.
        """
        
        access_list = [
            'get_device_details',
            'get_auth_list',
            'get_device_list',
            'post_logout',
            'post_token_refresh',
            'get_cameras_detail',
            'get_stream',
            'get_all_live_feeds',
            'get_alerts_list',
            'get_alerts_detail',
            'get_get_alerts_by_voice'
            # Device configuration
            'get_device_config_list',
            'post_device_config_list',
            'get_device_config_detail',
            'patch_device_config_detail',
            'delete_device_config_detail',
            'get_device_config_device',
            'post_send_edge_config',
            'get_role_list',
            'get_sensor_alerts_list',
        ]

        operator_endpoints = [
            endpoint for endpoint in endpoints 
            if endpoint.name in access_list
        ]

        view_access, _ = Permission.objects.get_or_create(
            name='view_access',
            defaults={'description': 'View access for live feeds and basic alerts'}
        )

        view_access.api_endpoints.set(operator_endpoints)
 
        operator_role, created = Role.objects.get_or_create(name='operator')

        if created:
             self.stdout.write("  ➕ Created Role: operator")

        operator_role.permissions.set([view_access])
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Operator role created/updated with 'view_access' covering {len(operator_endpoints)} endpoints.")
        )