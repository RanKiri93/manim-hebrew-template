# עברית + מתמטיקה ב־Manim (`hebrew_utils`)

**English:** [`README.md`](README.md)

פרויקט זה מיועד למורים ולמפתחי תוכן: הוא מאפשר לשלב **טקסט בעברית** ו**מתמטיקה ב־LaTeX בתוך שורה אחת** באובייקט [`Tex`](https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.Tex.html) של Manim, ואז להנפיש את השורה בסדר הגיוני: עברית בסדר **מימין לשמאל** (כמו כתיבה), ומתמטיקה בסדר **שמאל לימין** בתוך כל נוסחה.

כל הלוגיקה נמצאת בקובץ **`hebrew_utils.py`**. יש לייבא אותו מקובץ הסצנה שלכם ולהגדיר את תבנית ה־LaTeX פעם אחת (ראו למטה).

**אינדקס גליפים למתמטיקה (למפתחים):** `python tools/glyph_index_preview/server.py` ואז http://127.0.0.1:8765/ — מציג `MathTex` עם מספרים על הגליפים בסדר LTR. פרטים ב־`tools/glyph_index_preview/README.md`.

**יוצר קוד לשורות ולצירים (ממשק בעברית):** פתחו בדפדפן את `tools/tex_line_codegen/index.html` — לשוניות **יוצר שורות** (שורות עברית + `Tex` / `SmartHebWrite`, גופן, צבעים, משכי זמן, קו תחתון אופציונלי) ו־**צירים וגרפים** (`Axes` / `NumberPlane`, `run_time`/`wait`, `play` מקביל, גרפים ונקודות). ראו `tools/tex_line_codegen/README.md`.

**MCP (ללקוחות LLM):** שרת אופציונלי ליצירת קוד לצירים — `tools/hebrewmanim_mcp/`. ראו `tools/hebrewmanim_mcp/README.md`.

**GitHub:** המקור הרשמי הוא **[RanKiri93/manim-hebrew-template](https://github.com/RanKiri93/manim-hebrew-template)**. הנחיות דחיפה: [`docs/GITHUB.md`](docs/GITHUB.md).

---

## דרישות

- **Manim** (גרסת Community מתאימה).
- **XeLaTeX** — התבנית העברית משתמשת ב־`xelatex`, לא ב־`latex`.
- **גופן עברי** במערכת. ברירת המחדל ב־`get_hebrew_template()` היא **David Libre**; אפשר להתקין או להעביר שם גופן אחר.

---

## 1. הפעלת התבנית העברית

Manim חייב לקמפל עם אותה תבנית כמו שאר העזרים. בתחילת קובץ הסצנה (אחרי הייבוא):

```python
from hebrew_utils import get_hebrew_template
from manim import config

config.tex_template = get_hebrew_template()  # אופציונלי: get_hebrew_template("שם הגופן")
```

או קריאה אחת ל־`enable_hebrew_globally()` — אותה פעולה בפנים.

**גודל מתמטיקה בשורה:** ה־`$...$` הוא מתמטיקה **inline** — לא משוואת תצוגה מלאה. אם הנוסחאות נראות **גדולות מדי**, התבנית מגדירה `\everymath{\textstyle}` ו־`\DeclareMathSizes` כדי להקטין מעט את המתמטיקה ביחס לגוף הטקסט. ניתן לכוון עם `get_hebrew_template(math_pt_smaller=...)` או `explicit_math_styles=False`.

---

## 2. בניית שורה מעורבת (עברית + מתמטיקה)

### אובייקט `Tex` אחד, כמה ארגומנטים מחרוזת

**כל** נוסחה inline ב**ארגומון Python נפרד** כמחרוזת בצורה **`"$...$"`** (בלוק מתמטיקה אחד לכל ארגומון). טקסט עברי רגיל בארגומונים נפרדים.

**נכון:**

```python
tex_parts = (
    "משפט ראשון ",
    r"$\sin{(x)}$",
    " משפט שני ",
    r"$\cos{(x)}$",
)
text = Tex(*tex_parts)
```

**למה:** Manim שומר את זה כ־`text.tex_strings`. העזרים משתמשים ברשימה כדי לדעת **אילו** חלקים הם מתמטיקה ובאיזה **סדר** להנפיש — גם כש־RTL מסדר ויזואלית אחרת.

**להימנע:** מחרוזת אחת ארוכה עם כמה בלוקי `$...$` — מאבדים API נקי והכלי קשה יותר לתחזוקה.

### סימני דולר לא "מצוירים"

ה־`$` מסמנים מתמטיקה ב־LaTeX; בדרך כלל **אין** להם path נפרד ב־SVG. הזיהוי נעשה מ־**Python** (`tex_strings`), לא מחיפוש אחר גליפי דולר.

---

## 3. הנפשה: `SmartHebWrite`

`SmartHebWrite` מנגן הנפשה לכל **מקטע לפי סדר `tex_strings`** (`0, 1, 2, …`): קטעי עברית בסגנון RTL; בכל קטע מתמטיקה — `Write` על הגליפים בסדר **מקומי** משמאל לימין.

```python
from hebrew_utils import SmartHebWrite

self.play(SmartHebWrite(text, tex_strings_source=tex_parts))
```

- מומלץ להעביר **`tex_strings_source`** עם אותה tuple שבה השתמשתם ב־`Tex(*tex_parts)`.
- **`reverse_math_indices=True`** — בתוך כל נוסחה, לצייר גליפים מהאינדקס האחרון לראשון (לדיבוג או אפקט).

אם XeLaTeX **מאחד** קבוצות ב־SVG (נפוץ בעברית), `hebrew_utils` עדיין משייך paths ל־`tex_strings` הנכון באמצעות היוריסטיקות מרחביות + סדר מקור. שורות קיצוניות עשויות לדרוש סימון `MANIM_MATH_MARK` או פיצול ליותר ארגומני `Tex`.

### צביעת מקטע

- כאשר `len(tex.submobjects) == len(tex.tex_strings)`, אפשר `tex[i].set_color(...)`.
- כשהקבוצות מתמזגות, `tex_to_color_map` עלול להיכשל. השתמשו ב־**`set_tex_segment_color(tex, segment_index=i, color=..., tex_strings_source=parts)`**.

דוגמה: `tex_coloring_scene.py` (`TexColoringDemo`).

### `run_time` שונה לכל מקטע והפסקות

להנפיש כל חלק בנפרד עם משכים שונים או `wait` בין חלקים — לולאה עם `smart_heb_write_segment`:

```python
from hebrew_utils import smart_heb_write_segment

segment_run_times = (1.0, 0.75, 1.25, 0.85, 1.1)

for i in range(len(tex_parts)):
    self.play(
        smart_heb_write_segment(
            text,
            segment_index=i,
            tex_strings_source=tex_parts,
            run_time=segment_run_times[i],
        ),
    )
    if i == 2:
        self.wait(1)
```

דוגמה מינימלית: `segment_pause_scene.py` (`SegmentPauseDemo`).

למשך **אחד** לכל השורה עם `SmartHebWrite` בודד: `self.play(SmartHebWrite(...), run_time=T)`.

### ברירת מחדל ל־lag (`SmartHebWrite`)

בתוך `SmartHebWrite`, המקטעים מורכבים ב־`AnimationGroup` עם `lag_ratio` כמוגדר ב־**`_SMART_HEB_WRITE_SEGMENT_LAG_RATIO`** ב־`hebrew_utils.py`. ניתן לכוון שם את "המעבר" בין עברית למתמטיקה.

---

## 4. בניין נוסף (טבלה מקוצרת)

| שם | תפקיד |
|------|------|
| **`HebWrite`** | `Write` לעברית בלבד — מגב שמאלה והפיכת כיוון מכחול. |
| **`resolve_tex_inline_math_glyphs`** | גליפי מתמטיקה לנוסחה אחת, בסדר LTR. |
| **`indices_of_inline_math_tex_args`** | אילו אינדקסים ב־`parts` הם `$...$`. |
| **`math_formula_write_animation`** | שרשרת `Write` לנוסחה מרשימת גליפים. |
| **`FadeInMathTexIndexLabels`** | מספרים דיאגנוסטיים על גליפי מתמטיקה. |
| **`set_tex_segment_color`** | צביעת מקטע לפי אינדקס ב־`tex_strings`. |
| **`smart_heb_write_segment`** | הנפשת מקטע בודד + `run_time`. |
| **`MANIM_MATH_MARK`** | סימון בלתי נראה לבידוד ב־SVG (מתקדם). |

---

## 5. אופציונלי: סימון מתמטיקה בלתי נראה

```python
from hebrew_utils import MANIM_MATH_MARK, tex_extra_kwargs_for_isolated_math_marker

parts = ("טקסט ", f"$x^2{MANIM_MATH_MARK}$", " סוף")
t = Tex(*parts, **tex_extra_kwargs_for_isolated_math_marker())
```

המאקרו מוגדר ב־`get_hebrew_template()`; לא אמור להוסיף דיו נראה.

---

## 6. רינדור סצנה

מתיקיית הפרויקט:

```bash
manim -pql your_scene.py YourSceneName
```

`-ql` — איכות תצוגה מהירה; `-qh` — איכות גבוהה יותר. `-p` פותח נגן בסיום.

---

## 7. פתרון תקלות

| תסמין | משמעות נפוצה |
|--------|----------------|
| "Could not find SVG group for tex part …" | לעיתים **נורמלי** בעברית + XeLaTeX. **`resolve_tex_inline_math_glyphs`** עדיין כולל fallback מרחבי. |
| סדר ציור שגוי **בתוך** נוסחה | בדקו `math_arg_index` כשיש **כמה** בלוקי `$...$`. |
| סדר **סיפורי** שגוי בין מקטעים | ודאו ש־**אותה** tuple מועברת ל־`Tex` ול־`tex_strings_source`, ושכל נוסחה ב**ארגומון נפרד**. |

---

## 8. תאימות

המודול כתוב עבור **Manim Community**. בפורקים אחרים ייתכנו שינויים קטנים בייבוא או ב־API.

---

בהצלחה בהכנת הסרטונים.
