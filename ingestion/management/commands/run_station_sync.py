from django.core.management.base import BaseCommand

from ingestion.tasks import task_sync_stations

class Command(BaseCommand):

    help: str = 'Executa manualmente a sincronização de metadados das estações.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando processo manual de sincronição...'))
        # Saída no terminal com cor amarela

        self.stdout.write(self.style.SUCCESS("Processo enfileirado no Celery com sucesso!"))

        result = task_sync_stations()

        self.stdout.write(self.style.SUCCESS(f"Sucesso! Resultado: {result}"))
