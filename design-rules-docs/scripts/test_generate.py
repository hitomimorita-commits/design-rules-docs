import copy
import json
from pathlib import Path
import tempfile
import unittest
import generate as g

BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'example.json').read_text())
class GeneratorTests(unittest.TestCase):
 def test_all_layouts(self):
  text,report=g.generate(DATA,BASE)
  self.assertEqual(report['slides'],13)
  self.assertEqual(text.count('<section class="slide '),13)
  self.assertIn('data:font/ttf;base64,',text)
  self.assertIn('data:image/png;base64,',text)
 def test_unknown_style_rejected(self):
  d=copy.deepcopy(DATA);d['slides'][1]['icon']='sparkles'
  with self.assertRaises(ValueError):g.validate(d)
 def test_emoji_rejected(self):
  with self.assertRaises(ValueError):g.clean('内容✨')
 def test_nan_rejected(self):
  for bad in [float('nan'),float('inf'),True]:
   with self.assertRaises(ValueError):g.number(bad)
 def test_source_required(self):
  d=copy.deepcopy(DATA);del d['slides'][8]['source']
  with self.assertRaises(ValueError):g.validate(d)
 def test_causality_requires_evidence(self):
  d=copy.deepcopy(DATA);d['slides'][4]['relation']='causal'
  with self.assertRaises(ValueError):g.validate(d)
 def test_alignment_is_whitelisted(self):
  d=copy.deepcopy(DATA);d['slides'][7]['align']=['left','right','right;display:none']
  with self.assertRaises(ValueError):g.validate(d)
 def test_dimension_mismatch(self):
  d=copy.deepcopy(DATA);d['slides'][9]['series'][0]['values'].pop()
  with self.assertRaises(ValueError):g.validate(d)
 def test_zero_negative_pie_rejected(self):
  d=copy.deepcopy(DATA);d['slides'][10]['values'][0]=0
  with self.assertRaises(ValueError):g.validate(d)
 def test_file_traversal(self):
  with self.assertRaises(ValueError):g.image_asset('../secret.png',BASE)
 def test_escape(self):
  self.assertNotIn('<script>',g.E('<script>'))
 def test_theme_contrast(self):
  for name in g.THEMES:
   d=copy.deepcopy(DATA);d['theme']=name;g.validate(d)
 def test_negative_bars_and_constant_line(self):
  d=copy.deepcopy(DATA);d['slides'][8]['values']=[-20,0,10]
  d['slides'][9]['series']=[{'name':'一定','values':[0,0,0,0]}]
  doc,report=g.generate(d,BASE)
  self.assertTrue('x="NaN' not in doc and 'y="NaN' not in doc)
 def test_long_text_rejected(self):
  d=copy.deepcopy(DATA);d['slides'][1]['items']=['あ'*81]
  with self.assertRaises(ValueError):g.validate(d)
if __name__=='__main__':unittest.main()
