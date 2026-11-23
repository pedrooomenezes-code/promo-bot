import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot import ml, regras, textos

TZ = ZoneInfo("America/Sao_Paulo")
CFG = {"desconto_minimo": 15, "queda_minima": 10, "janela_dias": 30, "dias_minimos_historico": 5,
       "intervalo_repost_dias": 3, "queda_para_repostar": 5, "max_posts_dia": 6,
       "intervalo_minutos": 40, "hora_inicio": 8, "hora_fim": 23}
AGORA = datetime(2026, 11, 27, 10, 0, tzinfo=TZ)


def hist(precos):
    return {(AGORA.date() - timedelta(days=i + 1)).isoformat(): p for i, p in enumerate(precos)}


def prod(preco, orig=None):
    return {"id": "MLB1", "titulo": "Air Fryer Mondial 4L Family Preta 127V", "preco": preco,
            "preco_original": orig, "foto": None, "full": True, "frete_gratis": True}


class Identificar(unittest.TestCase):
    def test_links(self):
        self.assertEqual(ml.identificar("https://produto.mercadolivre.com.br/MLB-3846051727-air-fryer-_JM"), ("item", "MLB3846051727"))
        self.assertEqual(ml.identificar("https://www.mercadolivre.com.br/fone/p/MLB19615316#reco"), ("produto", "MLB19615316"))
        self.assertEqual(ml.identificar("https://www.mercadolivre.com.br/fone/p/MLB19615316?pdp_filters=item_id:MLB3999999999"), ("item", "MLB3999999999"))


class Avaliar(unittest.TestCase):
    def test_desconto_do_anuncio(self):
        d = regras.avaliar(prod(250, 400), {}, CFG, AGORA)
        self.assertEqual((d["motivo"], d["off"]), ("desconto", 38))

    def test_desconto_maquiado_e_barrado(self):
        # Sempre custou 250; "de 400 por 250" não é promoção.
        self.assertIsNone(regras.avaliar(prod(250, 400), hist([250] * 10), CFG, AGORA))

    def test_queda_no_historico(self):
        d = regras.avaliar(prod(270), hist([320] * 10), CFG, AGORA)
        self.assertEqual(d["motivo"], "queda")
        self.assertIsNone(d["de"])

    def test_sem_historico_suficiente(self):
        self.assertIsNone(regras.avaliar(prod(270), hist([320] * 3), CFG, AGORA))

    def test_preco_alvo(self):
        self.assertEqual(regras.avaliar(prod(240), {}, CFG, AGORA, 250)["motivo"], "alvo")


class Agenda(unittest.TestCase):
    def test_intervalo_e_limite(self):
        p = {}
        t1 = regras.proximo_horario(p, CFG, AGORA)
        p["a"] = {"agendado": t1.isoformat(), "quando": AGORA.isoformat(), "preco": 1}
        t2 = regras.proximo_horario(p, CFG, AGORA)
        self.assertEqual(t2 - t1, timedelta(minutes=40))
        for i in range(6):
            p[f"x{i}"] = {"agendado": AGORA.isoformat(), "quando": AGORA.isoformat(), "preco": 1}
        self.assertIsNone(regras.proximo_horario(p, CFG, AGORA))

    def test_madrugada_espera_8h(self):
        t = regras.proximo_horario({}, CFG, AGORA.replace(hour=6))
        self.assertEqual(t.hour, 8)

    def test_repost(self):
        p = {"MLB1": {"quando": AGORA.isoformat(), "preco": 300}}
        self.assertFalse(regras.pode_repostar(p, "MLB1", 295, CFG, AGORA))
        self.assertTrue(regras.pode_repostar(p, "MLB1", 280, CFG, AGORA))
        self.assertTrue(regras.pode_repostar(p, "MLB1", 300, CFG, AGORA + timedelta(days=3)))


class Textos(unittest.TestCase):
    def test_textos(self):
        for _ in range(30):
            t, _m = textos.montar(prod(249.9, 399.9), {"motivo": "desconto", "de": 399.9, "off": 38},
                                  "https://mercadolivre.com/sec/abc", "casa")
            self.assertIn("249,90", t)
            self.assertLessEqual(textos.tamanho_x(t), 280)
            t, _m = textos.montar(prod(270), {"motivo": "queda", "de": None, "off": 15}, "https://x.y/z")
            self.assertNotIn("De R$", t)
            self.assertNotIn("Menor preço", t)
        self.assertEqual(textos.brl(1299.0), "1.299")


if __name__ == "__main__":
    unittest.main()
