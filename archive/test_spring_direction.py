#!/usr/bin/env python
"""Verify spring force direction logic"""

import numpy as np

print("="*60)
print("SPRING FORCE DIRECTION VERIFICATION")
print("="*60)

# Spring physics: F = k * (current_length - rest_length)
# Positive F → spring stretched → pulls nodes together (tension)
# Negative F → spring compressed → pushes nodes apart (compression)

scenarios = [
    ("Stretched spring (rest < current)", 0.9, 1.0),
    ("Neutral spring (rest = current)", 1.0, 1.0),
    ("Compressed spring (rest > current)", 1.1, 1.0),
]

k = 1000.0  # Spring stiffness

print("\nFor vertical spring between bottom and top nodes:")
print("(positive force = upward, negative = downward)\n")

for name, rest, current in scenarios:
    force = k * (current - rest)
    direction = "UPWARD" if force > 0 else "DOWNWARD" if force < 0 else "ZERO"

    print(f"{name}:")
    print(f"  rest_length = {rest}m, current_length = {current}m")
    print(f"  Force = {force:.1f}N ({direction})")

    if rest < current:
        print(f"  → Spring is STRETCHED → pulls nodes together (contracts cube)")
    elif rest > current:
        print(f"  → Spring is COMPRESSED → pushes nodes apart (expands cube)")
    else:
        print(f"  → Spring is NEUTRAL → no force")
    print()

print("="*60)
print("CONCLUSION:")
print("="*60)
print("\nFor ground collision scenario:")
print("- Bottom nodes hit ground (Y=0)")
print("- Top nodes continue down due to momentum")
print("- Vertical springs get COMPRESSED (current < rest)")
print()
print("If rest_length > current_length (pre-compressed):")
print("  → Spring force is NEGATIVE (downward)")
print("  → But spring is compressed, so it PUSHES nodes apart")
print("  → Top nodes get pushed UPWARD → EXPLOSION!")
print()
print("If rest_length < current_length (pre-stretched):")
print("  → Spring force is POSITIVE (upward)")
print("  → But spring is stretched, so it PULLS nodes together")
print("  → Top nodes get pulled DOWNWARD → Cube compresses")
print()
print("If rest_length = current_length (neutral):")
print("  → When compressed: force pushes apart → top goes UP")
print("  → When stretched: force pulls together → top goes DOWN")
print("  → Need to start STRETCHED to resist compression!")
