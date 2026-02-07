from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def build_bom(measurements: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build a suggested BOM based on measurements.

    Example:
        >>> result = build_bom({
        ...     "puntos_rj45": 18,
        ...     "reserva_puertos": 0.15,
        ...     "m_por_punto": 28,
        ...     "margen_cable": 0.1,
        ...     "wifi_aps": 2,
        ...     "switch_tipo": "auto",
        ...     "u_estimadas": 10,
        ... })
        >>> any(i["ref"] == "KEYSTONE" and i["qty"] == 18 for i in result)
        True
        >>> any(i["ref"].startswith("PATCH_PANEL_") for i in result)
        True
    """
    m = _normalize(measurements)
    lines: list[dict[str, Any]] = []

    puntos = m.puntos
    reserva = m.reserva
    puertos = math.ceil(puntos * (1 + reserva))

    # Keystones
    if puntos > 0:
        lines.append({"ref": "KEYSTONE", "qty": puntos, "reason": "Uno por punto RJ45"})

    # Rosetas dobles
    if puntos > 0:
        rosetas = math.ceil(puntos / 2)
        lines.append({"ref": "ROSETA_DOBLE", "qty": rosetas, "reason": "Dobles, 2 tomas"})

    # Patch panel 12/24/48 según puertos
    if puertos > 0:
        panel = _choose_patch_panel(puertos)
        lines.append(
            {
                "ref": f"PATCH_PANEL_{panel}",
                "qty": 1,
                "reason": f"Para {puertos} puertos con reserva",
            }
        )

    # Latiguillos armario
    if puertos > 0:
        lines.append(
            {
                "ref": "LATIGUILLO_ARMARIO",
                "qty": puertos,
                "reason": "Uno por puerto en rack",
            }
        )

    # Cable por bobinas 305m
    if m.m_total > 0:
        total_m = math.ceil(m.m_total * (1 + m.margen_cable))
        bobinas = math.ceil(total_m / 305)
        lines.append(
            {
                "ref": "CABLE_CAT6_305M",
                "qty": bobinas,
                "reason": f"{total_m} m con margen en bobinas de 305m",
            }
        )

    # Switch 24/48, PoE si wifi_aps > 0
    if puertos > 0:
        switch_ports = 48 if puertos > 24 else 24
        poe = m.wifi_aps > 0
        ref = f"SWITCH_{switch_ports}{'_POE' if poe else ''}"
        reason = f"{puertos} puertos con reserva"
        if poe:
            reason += " y WiFi APs"
        lines.append({"ref": ref, "qty": 1, "reason": reason})

    # Rack sugerido según U estimadas + margen
    if m.u_estimadas > 0:
        u_target = math.ceil(m.u_estimadas * 1.2)
        rack_u = _choose_rack_u(u_target)
        lines.append(
            {
                "ref": f"RACK_{rack_u}U",
                "qty": 1,
                "reason": f"{m.u_estimadas}U + margen",
            }
        )
        lines.append({"ref": "RACK_PDU", "qty": 1, "reason": "Accesorio minimo"})
        lines.append({"ref": "RACK_KIT_M6", "qty": 1, "reason": "Accesorio minimo"})
        lines.append({"ref": "RACK_GUIA_PASACABLES", "qty": 1, "reason": "Accesorio minimo"})

    # Canaletas por tipo
    for tipo, qty in m.canaletas.items():
        if qty > 0:
            lines.append({"ref": f"CANALETA_{tipo}".upper(), "qty": qty, "reason": "Canaleta por tipo"})

    return lines


@dataclass
class _Meas:
    puntos: int
    reserva: float
    m_total: float
    margen_cable: float
    canaletas: dict[str, float]
    wifi_aps: int
    u_estimadas: int


def _normalize(measurements: dict[str, Any]) -> _Meas:
    puntos = int(measurements.get("puntos_rj45", 0) or 0)
    reserva = float(measurements.get("reserva_puertos", 0) or 0)
    margen_cable = float(measurements.get("margen_cable", 0) or 0)
    wifi_aps = int(measurements.get("wifi_aps", 0) or 0)
    u_estimadas = int(measurements.get("u_estimadas", 0) or 0)

    m_cable = measurements.get("m_cable")
    m_por_punto = measurements.get("m_por_punto")
    if m_cable is None and m_por_punto is None:
        m_total = 0.0
    elif m_cable is not None:
        m_total = float(m_cable or 0)
    else:
        m_total = float(m_por_punto or 0) * puntos

    canaletas = measurements.get("canaletas") or {}
    if not isinstance(canaletas, dict):
        canaletas = {}

    return _Meas(
        puntos=puntos,
        reserva=reserva,
        m_total=m_total,
        margen_cable=margen_cable,
        canaletas={str(k): float(v or 0) for k, v in canaletas.items()},
        wifi_aps=wifi_aps,
        u_estimadas=u_estimadas,
    )


def _choose_patch_panel(puertos: int) -> int:
    if puertos <= 12:
        return 12
    if puertos <= 24:
        return 24
    return 48


def _choose_rack_u(u_target: int) -> int:
    for u in [6, 9, 12, 18, 24]:
        if u_target <= u:
            return u
    return 24
