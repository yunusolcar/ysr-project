import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ysr.models import Question, Section

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "questions.json"


class Command(BaseCommand):
    help = "questions.json dosyasındaki bölümleri ve soruları veritabanına yükler."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH))

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Dosya bulunamadı: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))

        sections = {}
        for item in data["sections"]:
            item = dict(item)
            code = item.pop("code")
            section, _ = Section.objects.update_or_create(code=code, defaults=item)
            sections[code] = section

        created = updated = 0
        questions = {}
        for item in data["questions"]:
            item = dict(item)
            code = item.pop("code")
            section_code = item.pop("section")
            parent_code = item.pop("parent", None)

            if section_code not in sections:
                raise CommandError(f"Soru {code}: bilinmeyen bölüm '{section_code}'")
            if parent_code and parent_code not in questions:
                raise CommandError(
                    f"Soru {code}: üst madde '{parent_code}' dosyada bu sorudan önce tanımlı olmalı"
                )

            item["section"] = sections[section_code]
            item["parent"] = questions.get(parent_code)

            question, was_created = Question.objects.update_or_create(
                code=code, defaults=item
            )
            questions[code] = question
            created += was_created
            updated += not was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamam: {len(sections)} bölüm, {created} yeni soru, {updated} güncellenen soru."
            )
        )
