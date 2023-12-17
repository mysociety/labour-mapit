from django.core.management.base import LabelCommand, CommandError

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
        result = BranchCSVImporter.import_from_csv(
            label, purge=options["purge"], commit=options["commit"], generation=None
        )
        if result["error"]:
            raise CommandError(result["error"])
        self.stdout.write(f"Created: {result['created']}\nUpdated: {result['updated']}")
        if result["warnings"]:
            self.stdout.write(f"Warnings: {len(result['warnings'])}")
            self.stdout.write("\n".join(result["warnings"]))
