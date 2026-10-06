from diputado.core import extractors as ex


def test_lookalike_domain_and_risky_tld():
    r = ex.extract("Correos: abone 1,99 € en https://correos-aduanas.top/pago")
    assert r["flags"]["dominio_imitado"] and r["flags"]["tld_riesgo"] and r["flags"]["pago"]
    assert r["dominios"][0]["lookalike_of"] == "correos.es"
    assert r["importes"] == ["1,99 €"]


def test_official_domain_is_not_flagged():
    r = ex.extract("Consulta tu envío en https://www.correos.es/seguimiento")
    assert r["dominios"][0]["official"]
    assert not r["flags"]["dominio_imitado"]


def test_code_request_triggers_hard_rule():
    r = ex.extract("Le llamo del banco, necesito que me diga el código que le ha llegado por SMS")
    assert r["flags"]["pide_codigo"] and r["hard_rule"]


def test_legitimate_otp_disclaimer_disables_code_rule():
    r = ex.extract("Tu código de verificación es 482913. No lo compartas con nadie, ni siquiera con nosotros.")
    assert r["aviso_legitimo"]
    assert not r["flags"]["pide_codigo"] and not r["hard_rule"]


def test_remote_access_app():
    r = ex.extract("Para solucionarlo instale AnyDesk y deme el número que aparece")
    assert r["flags"]["remoto"] and r["hard_rule"]


def test_fake_relative_and_iban():
    r = ex.extract("Hola mamá, este es mi número nuevo. Hazme un bizum o transfiere a ES91 2100 0418 4502 0005 1332")
    assert r["flags"]["familiar"] and r["flags"]["iban"]
    assert r["red_flag_score"] > 0.4


def test_shortener():
    assert ex.extract("Revisa tu pedido: bit.ly/3xYz")["flags"]["acortador"]


def test_clean_message_has_low_score():
    r = ex.extract("Hola, ¿quedamos mañana a las cinco para tomar un café?")
    assert r["red_flag_score"] == 0 and not r["flags_humanos"]


def test_mask_pii():
    masked = ex.mask_pii("IBAN ES91 2100 0418 4502 0005 1332, tarjeta 4512 1234 5678 9012, DNI 12345678Z, tel 612 345 678")
    assert "2100 0418" not in masked and "1332" in masked
    assert "1234 5678" not in masked and "9012" in masked
    assert "12345678Z" not in masked
    assert "612 345" not in masked and masked.endswith("78")
