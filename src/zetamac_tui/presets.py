"""
Presets Module
====================================

This module provides common settings presets, which can be set using preset(presets.pre2)
"""

DEFAULT_SETTINGS = {
    "game_duration": 120.0,
    "cheat_mode": False,
    "no_log": 0,
	"addition_bounds": [2, 100, 2, 100],
	"multiplication_bounds": [2, 12, 2, 100],
	"operations": ["+", "-", "*", "/"],
	"flash_digits": 1,
	"flash_duration": 1.0,
	"flash_number": 10,
    "save_settings_state": True,
}
"""
The default settings. 
"""

_DEFAULT_RUN = {
    "game_duration": 120.0,
	"addition_bounds": [2, 100, 2, 100],
	"multiplication_bounds": [2, 12, 2, 100],
	"operations": ["+", "-", "*", "/"],
}

pre0 = DEFAULT_SETTINGS # quick alias

pre1 = {
	"multiplication_bounds": [2, 12, 13, 20],
	"operations": ["*"],
}
"""
Times tables of (2 to 12) × (13 to 20)
Helpful to rote memorise times tables to 12x20
"""

pre2 = {
	"multiplication_bounds": [12, 12, 2, 100],
	"operations": ["/"],
}
"""
Division of (2 to 100) ÷ 12
Often steals time from your run
"""

pre3 = {
    "multiplication_bounds": [99, 99, 2, 12],
    "operations": ['*', '/'],
}

pre4 = {
	"multiplication_bounds": [1, 12, 1, 12],
	"operations": ["*", "/"]
}
"""
1-12 times tables
do you have the brain inferior to that of a 5 year old? then this is for you
"""

presets_dict = {
	"13-20 times tables": pre1,
	"division by 12": pre2,
    "multiplication and division by 99": pre3,
	"times tables": pre4,
}
"""
dict of the presets - with explanations, not for practical use
For normal use, either call by name, or using presets: list
"""

presets = [
	pre0,
	pre1,
	pre2,
	pre3,
    pre4,
]

