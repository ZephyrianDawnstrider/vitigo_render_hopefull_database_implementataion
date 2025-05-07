from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q
import random
from .models import Query

User = get_user_model()

def get_random_staff():
    """Get a random staff member with appropriate roles"""
    staff_roles = ['NURSE', 'DOCTOR', 'MEDICAL_ASSISTANT', 'ADMINISTRATOR'] 
    staff_users = User.objects.filter(
        Q(role__name__in=staff_roles) & 
        Q(is_active=True)
    ).exclude(
        Q(email='') | Q(email__isnull=True)
    )
    
    if staff_users.exists():
        return random.choice(staff_users)
    return None

@receiver(post_save, sender=Query)
def assign_random_staff(sender, instance, created, **kwargs):
    """Assign newly created queries to random staff members"""
    if created and not instance.assigned_to:
        random_staff = get_random_staff()
        if random_staff:
            instance.assigned_to = random_staff
            instance.save(update_fields=['assigned_to'])
            
            # Trigger notification for assignment
            from .utils import send_query_notification
            send_query_notification(instance, 'assigned', recipient=random_staff)