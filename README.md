# rusit

Набор утилит для работы с языком **РУСИТ 3.0**: переводчик с русского на РУСИТ, валидатор грамматики, токенизатор/объяснитель и инструменты для мини-корпуса.

## Возможности

- `RusitTranslator` — детерминированный русский → РУСИТ переводчик для простых предложений.
- `RusitValidator` — проверка порядка TAM-частиц, незавершённых реляционных частиц и вероятных русских флексий.
- `explain` — классификация токенов как лексем, грамматических частиц, реляционных частиц и пунктуации.
- `corpus` — создание демонстрационного CSV-корпуса и подсчёт точных/валидных переводов.

## CLI

```bash
python3 -m rusit.cli translate "Я прочитал новую книгу моего друга."
# я был кон чита новый книга моего у друг.

python3 -m rusit.cli translate --input ru.txt --output rusit.txt
# то же самое: -i ru.txt -o rusit.txt; '-' означает stdin/stdout
# знаки препинания сохраняются

python3 -m rusit.cli translate -i README.md -o README.rusit.md
# Markdown-разметка сохраняется; формат .md определяется автоматически

python3 -m rusit.cli translate -i document.txt --format markdown
# принудительно включить режим Markdown: --format markdown или --markdown

python3 -m rusit.cli validate "я был кон чита книга у брат"

python3 -m rusit.cli explain "ли ты чита книга?"

python3 -m rusit.cli corpus demo corpus.csv
python3 -m rusit.cli corpus score corpus.csv
```

## Python API

```python
from rusit import RusitTranslator, RusitValidator

translator = RusitTranslator()
print(translator.translate("Мы будем строить дом."))
print(translator.translate_markdown("# Заголовок\n\nТекст **жирный**."))

validator = RusitValidator()
print(validator.validate("мы буд строи дом").ok)
```

Для морфологии требуется `pymorphy3`; тесты запускаются через `pytest`.
