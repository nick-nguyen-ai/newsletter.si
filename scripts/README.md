# Asset generation

Requires **Pillow** and **librsvg2-bin** (`rsvg-convert`).

```bash
pip install Pillow
sudo apt-get install -y librsvg2-bin   # if needed

python3 scripts/generate_og.py              # assets/og/*.png
python3 scripts/generate_brand_options.py   # brand option favicon previews + compare.png
```
