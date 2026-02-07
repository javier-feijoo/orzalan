from services.bom import build_bom


def main() -> None:
    bom = build_bom(
        {
            "puntos_rj45": 26,
            "reserva_puertos": 0.2,
            "m_por_punto": 30,
            "margen_cable": 0.1,
            "wifi_aps": 3,
            "u_estimadas": 11,
            "canaletas": {"40x20": 12, "60x40": 8},
        }
    )
    refs = {i["ref"] for i in bom}
    assert "KEYSTONE" in refs
    assert "PATCH_PANEL_48" in refs
    assert "SWITCH_48_POE" in refs
    assert any(r.startswith("CANALETA_") for r in refs)
    print("OK")


if __name__ == "__main__":
    main()
