from django.core.management.base import LabelCommand

from mapit_labour.importers import BranchCSVImporter


class Command(LabelCommand):
    help = "Imports UK UPRNs from AddressBase Core"
    label = "<AddressBase Core CSV file>"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "--commit",
            action="store_true",
            dest="commit",
            default=False,
            help="Commit changes to database",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            dest="purge",
            default=False,
            help="Delete all existing LBR areas first",
        )

    def handle_label(self, label: str, **options):
        BranchCSVImporter.import_from_csv(
            label, purge=options["purge"], commit=options["commit"]
        )
