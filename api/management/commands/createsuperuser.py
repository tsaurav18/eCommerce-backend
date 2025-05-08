from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import capfirst

class Command(BaseCommand):
    help = 'Create a superuser with custom user_id field'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address for the superuser')
        parser.add_argument('--name', type=str, help='Name of the superuser')
        parser.add_argument('--user_id', type=str, help='Custom user_id for the superuser')

    def handle(self, *args, **options):
        User = get_user_model()

        email = options.get('email')
        name = options.get('name')
        user_id = options.get('user_id')

        # Prompt user for email if not provided
        while not email:
            email = input('Email address: ').strip()

        # Prompt user for name if not provided
        while not name:
            name = input('Name: ').strip()

        # Prompt user for user_id if not provided
        while not user_id:
            user_id = input('User ID (leave blank for auto-generated): ').strip()
            if not user_id:
                user_id = User.objects.generate_random_id()
                self.stdout.write(f'Generated random user_id: {user_id}')

        # Check for uniqueness of user_id
        if User.objects.filter(user_id=user_id).exists():
            raise CommandError(f"user_id '{user_id}' already exists.")

        # Prompt user for password
        password = None
        while not password:
            password = self.get_password()

        # Create superuser
        user = User.objects.create_superuser(
            email=email,
            name=name,
            password=password,
            user_id=user_id
        )

        self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' created successfully with user_id '{user_id}'."))

    def get_password(self):
        import getpass
        password = getpass.getpass('Password: ')
        password2 = getpass.getpass('Password (again): ')
        if password != password2:
            self.stderr.write("Passwords do not match. Try again.")
            return None
        return password
