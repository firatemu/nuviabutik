"""
Geriye dönük uyumluluk: tüm çıktı canonical Nuvia şablonunu kullanır.
"""
from stoktakip.tsc_to_zpl_converter import generate_label


class AdvancedZPLGenerator:
    def generate_optimized_label(self, data):
        return generate_label(data)

    def generate_premium_label(self, data):
        return generate_label(data)

    def test_label(self):
        return generate_label(None)
