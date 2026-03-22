<div dir="rtl" align="right">

# Technion-HebrewManim

אנימציית טקסט עברי מעורב עם נוסחאות מתמטיות ב-[Manim Community](https://www.manim.community/).

## מה זה עושה?

הפרויקט פותר בעיה מרכזית: Manim לא תומך מהקופסה בכתיבה מונפשת של טקסט עברי (RTL) משולב עם מתמטיקה (LTR).
`SmartHebWrite` מנפיש כל קטע בכיוון הנכון — עברית מימין לשמאל, נוסחאות משמאל לימין — בסדר הקריאה הטבעי.

## מבנה הפרויקט

| קובץ | תיאור |
|---|---|
| `hebrew_utils.py` | המודול המרכזי — תבנית XeLaTeX, חלוקת גליפים, ואנימציית `SmartHebWrite` |
| `demo_scene.py` | סצנות דוגמה (מקרים פשוטים וקשים) |
| `line_builder.html` | כלי ויזואלי לבניית שורות — פתחו בדפדפן |

## התקנה

דרישות מוקדמות:
- Python 3.10+
- [Manim Community](https://docs.manim.community/en/stable/installation.html) (`pip install manim`)
- XeLaTeX (מגיע עם TeX Live / MiKTeX)
- גופן [David Libre](https://fonts.google.com/specimen/David+Libre) מותקן במערכת

## שימוש בסיסי

```python
from manim import Scene, Tex, config
from hebrew_utils import SmartHebWrite, get_hebrew_template

config.tex_template = get_hebrew_template()


class MyScene(Scene):
    def construct(self):
        parts = ("תהא ", r"$f(x)$", " פונקציה רציפה")
        text = Tex(*parts)
        self.play(SmartHebWrite(text, tex_strings_source=parts))
        self.wait(1)
```

הרצה:
```bash
manim render -pql my_scene.py MyScene
```

## צביעה ותזמון

ניתן לצבוע ולתזמן כל קטע בנפרד:

```python
from manim import RED, BLUE

parts = ("תהא ", r"$f(x)$", " רציפה ב-", r"$[a,b]$")
text = Tex(*parts)
self.play(SmartHebWrite(
    text,
    tex_strings_source=parts,
    colors={1: RED, 3: BLUE},       # נוסחאות בצבע
    run_times={1: 2.0, 3: 2.0},     # נוסחאות אטיות יותר
))
```

### פורמט הפרמטרים

`colors` ו-`run_times` מקבלים:
- **רשימה** (לפי סדר הקטעים): `[None, RED, None, BLUE]`
- **מילון** (לפי אינדקס): `{1: RED, 3: BLUE}`

## כלי בניית שורות

פתחו את `line_builder.html` בדפדפן. הכלי מאפשר:

1. **כתיבת שורה** — טקסט עברי מעורב עם `$...$`
2. **חלוקה אוטומטית** לקטעים (טקסט ומתמטיקה)
3. **פיצול** קטעי טקסט למקטעי-משנה (למשל, להפריד מילה שרוצים לצבוע)
4. **צביעה** — בחירת צבע Manim לכל קטע
5. **עיצוב** — Bold / Italic / Underline (עם פקודות LaTeX מתאימות לעברית ולמתמטיקה)
6. **תזמון** — `run_time` לכל קטע
7. **יצוא קוד** — קוד Python מוכן להדבקה, כולל אפשרות לסצנה שלמה לבדיקה

## שליטה מתקדמת

לשליטה מלאה (אנימציות מותאמות אישית, השהיות בין קטעים וכו'), השתמשו ב-`partition_segments` ישירות:

```python
from manim import Write
from hebrew_utils import partition_segments

parts = ("משפט: ", r"$E = mc^2$")
text = Tex(*parts)
segments = partition_segments(text, list(parts))

# segments[0] = VGroup של הגליפים העבריים
# segments[1] = VGroup של גליפי הנוסחה

segments[1].set_color(RED)
self.play(Write(segments[0], lag_ratio=0.5), run_time=1.0)
self.wait(0.5)
self.play(Write(segments[1], lag_ratio=0.1), run_time=2.0)
```

## פריסת פסקאות (מספר שורות)

כל שורה היא אובייקט `Tex` נפרד. סדרו אותן אנכית עם יישור ימין:

```python
lines = []
for line_parts in all_lines:
    t = Tex(*line_parts, font_size=36)
    lines.append(t)

group = VGroup(*lines).arrange(DOWN, aligned_edge=RIGHT)
group.to_edge(UP)
self.add(group)

for t, parts in zip(lines, all_lines):
    self.play(SmartHebWrite(t, tex_strings_source=parts))
```

## איך זה עובד מאחורי הקלעים

כש-XeLaTeX מרנדר טקסט עברי+מתמטיקה ל-SVG, Manim לעיתים לא מצליח לשייך גליפים לקטעי הטקסט המקוריים (SVG "קורס" לקבוצה אחת). `SmartHebWrite` פותר את זה באמצעות **spatial fingerprinting**:

1. כל נוסחה `$...$` מקומפלת בנפרד כ-`MathTex` ליצירת "טביעת אצבע" (מספר גליפים + מרווחים יחסיים).
2. הטביעה מותאמת לחלון הגליפים המתאים ב-`Tex` המלא.
3. הגליפים שנותרו (עברית) מחולקים בין קטעי הטקסט לפי הפערים הגדולים ביותר בציר ה-X, בסדר ימין-לשמאל.

</div>
