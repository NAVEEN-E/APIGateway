from django.db import models


class Manager(models.Manager):
    """
    Intended to be used for any overrides over the query interface
    across models (such as setting default values for
    bulk create ops, etc.).
    """

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        for obj in objs:
            obj.assign_default()

        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
        )
