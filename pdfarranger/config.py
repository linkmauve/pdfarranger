# Copyright (C) 2020 pdfarranger contributors
#
# pdfarranger is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import platform
import configparser
import os
import sys
import gettext
from gi.repository import Gdk
from gi.repository import Gtk

_ = gettext.gettext

# See https://gitlab.gnome.org/GNOME/gtk/-/blob/3.24.23/gdk/keynames.txt for list of keys
_DEFAULT_ACCELS = [
    ('delete', 'Delete'),
    ('page-size', 's'),
    ('crop', 'c'),
    ('hide', 'h'),
    ('rotate(90)', '<Primary>Right'),
    ('rotate(-90)', '<Primary>Left'),
    ('save', '<Primary>s'),
    ('save-as', '<Primary><Shift>s'),
    ('export-selection(2)', '<Primary>e'),
    ('export-all', '<Primary><Shift>e'),
    ('print', '<Primary>p'),
    ('close', '<Primary>w'),
    ('quit', '<Primary>q'),
    ('new', '<Primary>n'),
    ('open', '<Primary>o'),
    ('import', '<Primary>i'),
    ('zoom-in', 'plus KP_Add <Primary>plus <Primary>KP_Add'),
    ('zoom-out', 'minus KP_Subtract <Primary>minus <Primary>KP_Subtract'),
    ('zoom-fit', 'f'),
    ('fullscreen', 'F11'),
    ('undo', '<Primary>z'),
    ('redo', '<Primary>y'),
    ('cut', '<Primary>x'),
    ('copy', '<Primary>c'),
    ('paste(0)', '<Primary>v'),
    ('paste(1)', '<Primary><Shift>v'),
    ('paste(4)', '<Primary><Shift>o'),
    ('paste(5)', '<Primary><Shift>u'),
    ('select(0)', '<Primary>a'),
    ('select(1)', '<Primary><Shift>a'),
    ('main-menu', 'F10'),
    ('metadata', '<Alt>Return'),
    ('context-menu', '<Shift>F10 Menu'),
]


class Config(object):
    """Wrap a ConfigParser object for PDFArranger"""

    @staticmethod
    def __get_action_list(m, r):
        for i in range(m.get_n_items()):
            it = m.iterate_item_attributes(i)
            target, action = None, None
            while it.next():
                if it.get_name() == 'target':
                    target = it.get_value()
                elif it.get_name() == 'action':
                    action = it.get_value()
            if action is not None:
                action = action.get_string()[4:]
                if target is not None:
                    action += "({})".format(target)
                r.append(action)
            it = m.iterate_item_links(i)
            while it.next():
                Config.__get_action_list(it.get_value(), r)
        return r

    @staticmethod
    def _config_file(domain):
        """Return the location of the configuration file"""
        if os.name == 'nt' and getattr(sys, 'frozen', False):
            p = os.path.dirname(sys.executable)
            config_ini = os.path.join(p, 'config.ini')
            if os.path.isfile(config_ini):
                return config_ini
        home = os.path.expanduser("~")
        if platform.system() == 'Darwin':
            p = os.path.join(home, 'Library', 'Preferences')
        elif 'APPDATA' in os.environ:
            p = os.getenv('APPDATA')
        elif 'XDG_CONFIG_HOME' in os.environ:
            p = os.getenv('XDG_CONFIG_HOME')
        else:
            p = os.path.join(home, '.config')
        p = os.path.join(p, domain)
        os.makedirs(p, exist_ok=True)
        return os.path.join(p, 'config.ini')

    def __init__(self, domain, pdfarranger):
        self.pdfarranger = pdfarranger
        self.domain = domain
        self.data = configparser.ConfigParser()
        self.data.add_section('window')
        self.data.read(Config._config_file(domain))
        if 'preferences' not in self.data:
            self.data.add_section('preferences')
        if 'print-settings' not in self.data:
            self.data.add_section('print-settings')
        if 'accelerators' not in self.data:
            self.data.add_section('accelerators')
        a = self.data['accelerators']
        if 'enable_custom' not in a:
            a['enable_custom'] = 'false'
        enable_custom = a.getboolean('enable_custom')
        for k, v in _DEFAULT_ACCELS:
            if not enable_custom or k not in a:
                a[k] = v
        self.popup_menu_accels = [
            Gtk.accelerator_parse(x) for x in a["context-menu"].split()
        ]

    def is_popup_key_event(self, keyevent):
        for key, mods in self.popup_menu_accels:
            # `& mods` lets us ignore all other modifiers (e.g. numlock)
            if keyevent.state & mods == mods and keyevent.keyval == key:
                return True
        return False

    def window_size(self):
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        ds = monitors[0].get_geometry()
        return self.data.getint('window', 'width', fallback=int(min(700, ds.width / 2))), \
            self.data.getint('window', 'height', fallback=int(min(600, ds.height - 50)))

    def set_window_size(self, width, height):
        self.data.set('window', 'width', str(width))
        self.data.set('window', 'height', str(height))

    def maximized(self):
        return self.data.getboolean('window', 'maximized', fallback=False)

    def set_maximized(self, maximized):
        self.data.set('window', 'maximized', str(maximized))

    def zoom_level(self):
        return self.data.getint('preferences', 'zoom-level', fallback=0)

    def set_zoom_level(self, level):
        self.data.set('preferences', 'zoom-level', str(level))

    def content_loss_warning(self):
        return self.data.getboolean('preferences', 'content-loss-warning', fallback=True)

    def set_content_loss_warning(self, enabled):
        self.data.set('preferences', 'content-loss-warning', str(enabled))

    def show_save_warnings(self):
        return self.data.getboolean('preferences', 'show-save-warnings', fallback=True)

    def set_show_save_warnings(self, enabled):
        self.data.set('preferences', 'show-save-warnings', str(enabled))

    def language(self):
        return self.data.get('preferences', 'language', fallback="")

    def set_language(self, language):
        self.data.set('preferences', 'language', language)

    def theme(self):
        return self.data.get('preferences', 'theme', fallback="")

    def set_theme(self, theme):
        self.data.set('preferences', 'theme', theme)

    def scale_mode(self):
        return self.data.get('print-settings', 'scale-mode', fallback="PRINTABLE")

    def set_scale_mode(self, mode):
        self.data.set('print-settings', 'scale-mode', mode)

    def auto_rotate(self):
        return self.data.getboolean('print-settings', 'auto-rotate', fallback=False)

    def set_auto_rotate(self, enabled):
        self.data.set('print-settings', 'auto-rotate', str(enabled))

    def save(self):
        conffile = Config._config_file(self.domain)
        os.makedirs(os.path.dirname(conffile), exist_ok=True)
        with open(conffile, 'w') as f:
            self.data.write(f)

    def set_actions(self, builder):
        """
        Set the list of actions to which shortcuts may be associated.

        :param builder: A Gtk.Builder from which to get actions
        """
        actions = []
        for m in builder.get_objects():
            self.__get_action_list(m, actions)
        actions = set(actions)
        accels_section = self.data['accelerators']
        for a in actions:
            if a not in accels_section:
                accels_section[a] = ""
        # Have accelerators sorted in the .ini file (cosmetic)
        sortedaccels = [(k, v) for k, v in accels_section.items() if k != 'enable_custom']
        sortedaccels = sorted(sortedaccels)
        enable_custom = accels_section['enable_custom']
        accels_section.clear()
        accels_section['enable_custom'] = enable_custom
        accels_section.update(sortedaccels)

    def get_accels(self):
        """Return the accelerators for each actions."""
        return [
            (k, v.split())
            for k, v in self.data["accelerators"].items()
            if k != "enable_custom"
        ]

    def preferences_dialog(self, parent, localedir):
        """A dialog for some application preferences."""
        d = self.pdfarranger.uiXML.get_object('preferences')
        combo = self.pdfarranger.uiXML.get_object('languages')
        combo2 = self.pdfarranger.uiXML.get_object('theme')
        scale_mode = self.pdfarranger.uiXML.get_object('scale-mode')
        auto_rotate = self.pdfarranger.uiXML.get_object('auto-rotate')

        langs = []
        if os.path.isdir(localedir):
            langs = os.listdir(localedir)
        langs.append("en")
        langs.sort()
        languages = combo.get_model()
        for lan in langs:
            languages.append(lan)
        lang = self.language()
        if lang in langs:
            combo.set_selected(langs.index(lang) + 1)
        else:
            combo.set_selected(0)
        combo.connect('notify::selected', lambda combo, _param: self.combo_changed(combo, langs))

        theme = self.theme()
        themes = ['', 'light', 'dark']
        if theme in themes:
            combo2.set_selected(themes.index(theme))
        else:
            combo2.set_selected(0)
        combo2.connect('notify::selected', self.theme_changed)

        scale_modes = ['NONE', 'PRINTABLE', 'FULL']
        scale_mode.set_selected(scale_modes.index(self.scale_mode()))
        scale_mode.connect('notify::selected', self.scale_mode_changed)

        auto_rotate.set_active(self.auto_rotate())
        auto_rotate.connect('notify::active', self.auto_rotate_changed)

        d.present(parent)

    def combo_changed(self, combo, langs):
        selected = combo.get_selected()
        if selected == 0:
            self.set_language('')
        else:
            self.set_language(langs[selected - 1])

    def theme_changed(self, combo, _param):
        selected = combo.get_selected()
        theme = ['', 'light', 'dark'][selected]
        self.set_theme(theme)
        self.pdfarranger.set_color_scheme()

    def scale_mode_changed(self, combo, _param):
        selected = combo.get_selected()
        scale_mode = ['NONE', 'PRINTABLE', 'FULL'][selected]
        self.set_scale_mode(scale_mode)

    def auto_rotate_changed(self, combo, _param):
        active = combo.get_active()
        self.set_auto_rotate(active)
