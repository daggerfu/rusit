# rusit

Набор утилит для работы с языком **РУСИТ 5.3.1**: переводчик с русского на РУСИТ, валидатор грамматики, токенизатор/объяснитель и инструменты для мини-корпуса.

## Возможности

- `RusitTranslator` — детерминированный русский → РУСИТ переводчик для простых предложений.
- `RusitValidator` — проверка порядка TAM-частиц, незавершённых реляционных частиц и вероятных русских флексий.
- `explain` — классификация токенов как лексем, грамматических частиц, реляционных частиц и пунктуации.
- `repl` / `echo` — интерактивный построчный режим перевода (русский → РУСИТ).
- `corpus` — создание демонстрационного CSV-корпуса и подсчёт точных/валидных переводов.

## CLI

```bash
python3 -m rusit.cli translate "Я прочитал новую книгу моего друга."
# я кон чита новый книга мой у друг.

python3 -m rusit.cli translate --input ru.txt --output rusit.txt
# то же самое: -i ru.txt -o rusit.txt; '-' означает stdin/stdout
# знаки препинания сохраняются

python3 -m rusit.cli translate -i README.md -o README.rusit.md
# Markdown-разметка сохраняется; формат .md определяется автоматически

python3 -m rusit.cli translate -i document.txt --format markdown
# принудительно включить режим Markdown: --format markdown или --markdown

python3 -m rusit.cli translate "Я читаю книгу."
# синтаксический разбор через spaCy включён по умолчанию (нужна модель ru_core_news_sm)

python3 -m rusit.cli translate --no-spacy "Я читаю книгу."
# отключить spaCy и использовать только pymorphy3

python3 -m rusit.cli repl
# интерактивный режим (русский → РУСИТ), выход: Ctrl+D, Ctrl+C или /exit

python3 -m rusit.cli validate "я кон чита книга у брат"

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

Единственный лексикон — `rusit_lexicon.json` в корне репозитория; путь по умолчанию относительный, поэтому запускайте из корня или передавайте `lexicon_path` явно.

Для морфологии требуется `pymorphy3`; синтаксический разбор через `spaCy` включён по умолчанию (нужна установленная модель `ru_core_news_sm`, отключение — `use_spacy=False` или `--no-spacy`). Тесты запускаются через `pytest`.
