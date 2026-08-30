# rusit

Набор утилит для работы с языком **РУСИТ 3.0**: переводчик с русского на РУСИТ, валидатор грамматики, токенизатор/объяснитель и инструменты для мини-корпуса.

## Возможности

- `RusitTranslator` — детерминированный русский → РУСИТ переводчик для простых предложений.
- `RusitValidator` — проверка порядка TAM-частиц, незавершённых реляционных частиц и вероятных русских флексий.
- `explain` — классификация токенов как лексем, грамматических частиц, реляционных частиц и пунктуации.
- `corpus` — создание демонстрационного CSV-корпуса и подсчёт точных/валидных переводов.

## CLI

```bash
python -m rusit.cli translate "Я прочитал новую книгу моего друга."
# я был кон чита новый книга у я друг

python -m rusit.cli validate "я был кон чита книга у брат"

python -m rusit.cli explain "ли ты чита книга?"

python -m rusit.cli corpus demo corpus.csv
python -m rusit.cli corpus score corpus.csv
```

## Python API

```python
from rusit import RusitTranslator, RusitValidator

translator = RusitTranslator()
print(translator.translate("Мы будем строить дом."))

validator = RusitValidator()
print(validator.validate("мы буд строи дом").ok)
```

Проект намеренно использует только стандартную библиотеку Python, чтобы прототип запускался без тяжёлых NLP-зависимостей.
