from django.db import models
from django.utils.translation import gettext_lazy as _


class AlertStatus(models.TextChoices):
    ACTIVE = "Active", _("Active")
    COMPLETE = "Complete", _("Complete")
    INFERENCING = "Inferencing", _("Inferencing")
    HUMAN_VERIFICATION = "Human Verification", _("Human Verification")
    FAILED = "Failed", _("Failed")

    def __str__(self):
        return str(self.label)
