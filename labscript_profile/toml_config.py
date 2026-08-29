import configparser

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w


def as_config_list(value):
    """Return a labconfig value as a list of stripped strings.

    TOML gives options native types, so a path-list option may arrive either as
    a comma-separated string, as it always did under INI, or as a real TOML
    array. Accept both, and treat anything else as a single entry.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def load_toml_file(filename):
    with open(filename, 'rb') as f:
        return tomllib.load(f)


def dump_toml_file(filename, data):
    with open(filename, 'wb') as f:
        tomli_w.dump(data, f)


class TomlBasicInterpolation(configparser.BasicInterpolation):
    """Basic interpolation that leaves non-string TOML values alone."""

    def before_get(self, parser, section, option, value, defaults):
        if not isinstance(value, str):
            return value
        return super().before_get(parser, section, option, value, defaults)


class TomlConfigParser(configparser.ConfigParser):
    """ConfigParser variant that preserves native TOML values."""

    def __init__(self, *args, **kwargs):
        self.lowercase_keys_and_sections = kwargs.pop('lowercase_keys_and_sections', True)
        if self.lowercase_keys_and_sections:
            kwargs.setdefault('default_section', 'default')
        kwargs.setdefault('interpolation', TomlBasicInterpolation())
        super().__init__(*args, **kwargs)
        if not self.lowercase_keys_and_sections:
            self.optionxform = str

    def _canonical_section_name(self, section):
        if section is None:
            return None
        if not self.lowercase_keys_and_sections:
            return section
        return str(section).lower()

    def _normalize_loaded_sections(self):
        if not self.lowercase_keys_and_sections:
            return
        renamed_sections = {}
        migrated_defaults = {}
        for name, section_data in self._sections.items():
            canonical = self._canonical_section_name(name)
            if canonical == self.default_section:
                migrated_defaults.update(section_data)
                continue
            existing = renamed_sections.get(canonical)
            if existing is not None and existing is not section_data:
                raise configparser.DuplicateSectionError(canonical)
            renamed_sections[canonical] = section_data
        self._defaults.update(migrated_defaults)
        self._sections = renamed_sections
        self._proxies = {self.default_section: configparser.SectionProxy(self, self.default_section)}
        for canonical in renamed_sections:
            self._proxies[canonical] = configparser.SectionProxy(self, canonical)

    def add_section(self, section):
        return super().add_section(self._canonical_section_name(section))

    def has_section(self, section):
        return super().has_section(self._canonical_section_name(section))

    def options(self, section):
        return super().options(self._canonical_section_name(section))

    def has_option(self, section, option):
        return super().has_option(self._canonical_section_name(section), option)

    def remove_section(self, section):
        return super().remove_section(self._canonical_section_name(section))

    def remove_option(self, section, option):
        return super().remove_option(self._canonical_section_name(section), option)

    def __getitem__(self, key):
        return super().__getitem__(self._canonical_section_name(key))

    def set(self, section, option, value=None):
        section = self._canonical_section_name(section)
        if not section or section == self.default_section:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise configparser.NoSectionError(section) from None
        sectdict[self.optionxform(option)] = value

    def getboolean(
        self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET
    ):
        value = self.get(section, option, raw=raw, vars=vars, fallback=fallback)
        if value is fallback:
            return value
        if isinstance(value, bool):
            return value
        return self._convert_to_boolean(value)

    def get(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
        return super().get(
            self._canonical_section_name(section),
            option,
            raw=raw,
            vars=vars,
            fallback=fallback,
        )

    def items(self, section=configparser._UNSET, raw=False, vars=None):
        if section is configparser._UNSET:
            return super().items(section=section, raw=raw, vars=vars)
        return super().items(self._canonical_section_name(section), raw=raw, vars=vars)

    def read(self, filenames, encoding=None):
        read_ok = super().read(filenames, encoding=encoding)
        self._normalize_loaded_sections()
        return read_ok

    def read_toml(self, filename):
        data = load_toml_file(filename)
        if not isinstance(data, dict):
            raise TypeError("Top-level TOML document must be a mapping of sections")
        for section_name, section in data.items():
            if not isinstance(section, dict):
                raise TypeError(f"Section {section_name!r} must contain key/value pairs")
            section_name = self._canonical_section_name(section_name)
            if section_name != self.default_section and not self.has_section(section_name):
                self.add_section(section_name)
            for option, value in section.items():
                self.set(section_name, str(option), value)
        return [str(filename)]

    def to_toml_dict(self):
        data = {}
        if self.defaults():
            data[self.default_section] = dict(self.defaults())
        for section in self.sections():
            data[section] = dict(self._sections[section])
        return data

    def write_toml(self, filename):
        dump_toml_file(filename, self.to_toml_dict())
