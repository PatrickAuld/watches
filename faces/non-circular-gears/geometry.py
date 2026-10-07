"""Shared geometry for the Non-Circular Gears face.

Two identical elliptical gears, each pivoted at one focus, mesh with their
pivots one major axis apart. The driver turns uniformly; the follower, which
carries the hands, turns at a rate that swings between (1+e)/(1-e) and
(1-e)/(1+e) times the driver's.

Angles are dial angles in degrees: 0 at 12 o'clock, clockwise positive.
Design units are the 450 x 450 WFF canvas.
"""
from __future__ import annotations

import math

A = 48.0                 # semi-major axis of each pitch ellipse
E = 0.4                  # eccentricity
P = A * (1 - E * E)      # semi-latus rectum
R_MIN, R_MAX = A * (1 - E), A * (1 + E)
CENTER = (225.0, 225.0)                  # follower pivot, under the hands
DRIVER = (225.0, 225.0 + 2 * A)          # driver pivot, toward 6 o'clock
TEETH = 27               # odd: a tooth at periapsis meets a gap at apoapsis
ADDENDUM, DEDENDUM = 3.0, 3.4


def follower(u: float) -> float:
    """Follower (and hand) angle for a uniform driver angle u, both in degrees.

    g(u) = u + 2 atan(e sin u / (1 - e cos u)). The denominator never reaches
    zero, so g is continuous and g(u + 360) = g(u) + 360.
    """
    r = math.radians(u)
    return u + 2 * math.degrees(math.atan(E * math.sin(r) / (1 - E * math.cos(r))))


def follower_rate(u: float) -> float:
    """dg/du: (1 - e^2) / (1 - 2 e cos u + e^2)."""
    return (1 - E * E) / (1 - 2 * E * math.cos(math.radians(u)) + E * E)


def follower_expr(u: str) -> str:
    """WFF expression for follower(u). WFF trig works in radians."""
    return (f"({u} + 2 * deg(atan({E:g} * sin(rad({u})) / "
            f"(1 - {E:g} * cos(rad({u}))))))")


def pitch_radius(psi: float) -> float:
    """Focal radius of the pitch ellipse, psi in degrees from periapsis."""
    return P / (1 + E * math.cos(math.radians(psi)))


# In each gear's own frame the periapsis (short side) points to 12 o'clock.
# These are the Group rotations that place each gear for a driver angle u.
def follower_body(u: float) -> float:
    # The long side points along the hand; the short side faces the driver at :00.
    return follower(u) + 180


def driver_body(u: float) -> float:
    # Counter-rotates uniformly; its long side faces the follower at :00.
    return 180 - u


def minute_angle(minute: float) -> float:
    """Where the scale mark for a minute (or second) value sits."""
    return follower(6 * minute)
