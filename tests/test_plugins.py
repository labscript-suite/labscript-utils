import logging
import sys
import uuid
import warnings
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labscript_utils.plugins import (
    BasePlugin,
    Callback,
    DEFAULT_SETUP_PRIORITY,
    MenuBuilder,
    MenuContext,
    PluginManager,
    callback,
)


class FakeConfig(object):
    """Minimal stand-in for LabConfig, including the two behaviours that matter.

    A real config inherits its defaults section into every section, and returns
    native TOML types rather than strings. Modelling neither is what let the
    defaults-as-plugin-names bug survive in the first place.
    """

    def __init__(self, defaults=None):
        self.sections = {}
        self.defaults = dict(defaults or {})

    def has_section(self, name):
        return name in self.sections

    def add_section(self, name):
        self.sections[name] = {}

    def items(self, name):
        merged = dict(self.defaults)
        merged.update(self.sections[name])
        return list(merged.items())

    def has_option(self, section, option):
        return option in self.sections.get(section, {}) or option in self.defaults

    def get(self, section, option):
        if option in self.sections.get(section, {}):
            return self.sections[section][option]
        return self.defaults[option]

    def set(self, section, option, value):
        self.sections[section][option] = value

    def getboolean(self, section, option):
        value = self.get(section, option)
        if isinstance(value, bool):
            return value
        if str(value).lower() in ('true', 'yes', 'on', '1'):
            return True
        if str(value).lower() in ('false', 'no', 'off', '0'):
            return False
        raise ValueError('Not a boolean: %s' % value)


def test_callback_binds_as_method_and_keeps_priority():
    class Example(object):
        @callback(priority=5)
        def method(self, value):
            return self, value

    example = Example()

    assert isinstance(Example.__dict__['method'], Callback)
    assert Example.__dict__['method'].priority == 5
    assert example.method('value') == (example, 'value')


def test_base_plugin_defaults_are_no_ops():
    plugin = BasePlugin({'x': 1})

    assert plugin.initial_settings == {'x': 1}
    assert plugin.get_menu_class() is None
    assert plugin.get_notification_classes() == []
    assert plugin.get_setting_classes() == []
    assert plugin.get_event_handlers() is None
    assert plugin.get_callbacks() is None
    assert plugin.get_ui_contributions() == []
    assert plugin.get_menu_contributions() == []
    assert plugin.get_save_data() == {}


def make_plugin_package(tmp_path, modules):
    package = 'plugin_test_' + uuid.uuid4().hex
    package_dir = tmp_path / package
    plugins_dir = package_dir / 'plugins'
    plugins_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('')
    (plugins_dir / '__init__.py').write_text('')
    for name, source in modules.items():
        module_dir = plugins_dir / name
        module_dir.mkdir()
        (module_dir / '__init__.py').write_text(source)
    sys.path.insert(0, str(tmp_path))
    return package + '.plugins', plugins_dir


def make_manager(logger=None):
    return PluginManager(
        'package.plugins',
        'plugins',
        FakeConfig(),
        'app/plugins',
        logger=logger,
    )


class NoNotifications(object):
    def add_notification(self, notification_class):
        raise AssertionError('no notifications expected')

    def get_instance(self, notification_class):
        raise AssertionError('no notifications expected')


def test_discovery_defaults_config_and_imports_only_enabled_plugins(tmp_path):
    plugin_package, plugins_dir = make_plugin_package(
        tmp_path,
        {
            'enabled': 'class Plugin(object):\n    pass\n',
            'disabled': 'raise RuntimeError("should not import")\n',
        },
    )
    config = FakeConfig()
    manager = PluginManager(
        plugin_package,
        str(plugins_dir),
        config,
        'app/plugins',
        ['enabled'],
    )

    modules = manager.discover_modules()

    assert set(modules) == {'enabled'}
    assert config.sections['app/plugins']['enabled'] is True
    assert config.sections['app/plugins']['disabled'] is False


def test_instantiate_plugins_uses_saved_settings():
    class Plugin(object):
        def __init__(self, initial_settings):
            self.initial_settings = initial_settings

    manager = PluginManager(
        'package.plugins',
        'plugins',
        FakeConfig(),
        'app/plugins',
    )
    manager.modules = {'plugin': SimpleNamespace(Plugin=Plugin)}

    plugins = manager.instantiate_plugins({'plugin': {'answer': 42}})

    assert plugins['plugin'].initial_settings == {'answer': 42}


def test_get_event_handlers_sorts_legacy_callbacks_by_priority_and_logs_errors(caplog):
    class Slow(object):
        def get_callbacks(self):
            return {'event': self.on_event}

        @callback(priority=20)
        def on_event(self):
            pass

    class Fast(object):
        def get_callbacks(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self):
            pass

    class Broken(object):
        def get_callbacks(self):
            raise RuntimeError('broken')

    logger = logging.getLogger('test.plugins')
    manager = make_manager(logger=logger)
    manager.plugins = {
        'slow': Slow(),
        'broken': Broken(),
        'fast': Fast(),
    }

    with caplog.at_level(logging.ERROR, logger='test.plugins'):
        callbacks = manager.get_event_handlers('event')

    assert [callback.priority for callback in callbacks] == [5, 20]
    assert 'Error getting callbacks from' in caplog.text


def test_get_event_handlers_sorts_modern_handlers_by_priority():
    class Slow(object):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=20)
        def on_event(self):
            pass

    class Fast(object):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self):
            pass

    manager = make_manager()
    manager.plugins = {
        'slow': Slow(),
        'fast': Fast(),
    }

    callbacks = manager.get_event_handlers('event')

    assert [callback.priority for callback in callbacks] == [5, 20]


def test_get_callbacks_warns_and_delegates_to_get_event_handlers():
    class Plugin(object):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self):
            pass

    manager = make_manager()
    manager.plugins = {'plugin': Plugin()}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        callbacks = manager.get_callbacks('event')

    assert [callback.priority for callback in callbacks] == [5]
    assert len(caught) == 1
    assert 'PluginManager.get_callbacks() is deprecated' in str(caught[0].message)


def test_get_event_handlers_prefers_modern_hook_and_warns_for_legacy_one(caplog):
    class ModernAndLegacy(object):
        def get_event_handlers(self):
            return {'event': self.new_event}

        def get_callbacks(self):
            return {'event': self.old_event}

        @callback(priority=5)
        def new_event(self):
            pass

        @callback(priority=20)
        def old_event(self):
            pass

    class LegacyOnly(object):
        def get_callbacks(self):
            return {'event': self.old_event}

        @callback(priority=10)
        def old_event(self):
            pass

    logger = logging.getLogger('test.plugins')
    manager = make_manager(logger=logger)
    manager.plugins = {
        'modern_and_legacy': ModernAndLegacy(),
        'legacy_only': LegacyOnly(),
    }

    with caplog.at_level(logging.WARNING, logger='test.plugins'):
        first_callbacks = manager.get_event_handlers('event')
        second_callbacks = manager.get_event_handlers('event')

    assert [callback.priority for callback in first_callbacks] == [5, 10]
    assert [callback.priority for callback in second_callbacks] == [5, 10]
    warning_messages = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    assert sum('modern_and_legacy' in message for message in warning_messages) == 1
    assert sum('legacy_only' in message for message in warning_messages) == 1
    assert sum('get_callbacks()' in message for message in warning_messages) == 2


def test_setup_plugins_prefers_modern_settings_callback_and_warns(caplog):
    class Plugin(BasePlugin):
        def get_event_handlers(self):
            return {'settings_changed': self.new_settings_changed}

        def get_callbacks(self):
            return {'settings_changed': self.old_settings_changed}

        @callback(priority=5)
        def new_settings_changed(self):
            pass

        @callback(priority=20)
        def old_settings_changed(self):
            pass

    logger = logging.getLogger('test.plugins')
    manager = make_manager(logger=logger)
    manager.plugins = {'plugin': Plugin({})}

    with caplog.at_level(logging.WARNING, logger='test.plugins'):
        settings_pages, settings_callbacks = manager.setup_plugins(
            data={},
            notifications=NoNotifications(),
            menu_builder=MenuBuilder(),
            menubar=FakeMenu(),
        )
        callbacks = manager.get_event_handlers('settings_changed')

    assert settings_pages == []
    assert [callback.priority for callback in settings_callbacks] == [5]
    assert [callback.priority for callback in callbacks] == [5]
    warning_messages = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    assert sum('deprecated get_callbacks()' in message for message in warning_messages) == 1


def test_setup_plugins_warns_when_deprecated_menu_class_is_used(caplog):
    class Menu(object):
        def __init__(self, data):
            self.data = data

        def get_menu_items(self):
            return {'name': 'Legacy'}

    class Plugin(BasePlugin):
        def get_menu_class(self):
            return Menu

    logger = logging.getLogger('test.plugins')
    manager = make_manager(logger=logger)
    manager.plugins = {'plugin': Plugin({})}

    with caplog.at_level(logging.WARNING, logger='test.plugins'):
        manager.setup_plugins(
            data={'example': True},
            notifications=NoNotifications(),
            menu_builder=MenuBuilder(),
            menubar=FakeMenu(),
        )
        manager.setup_plugins(
            data={'example': True},
            notifications=NoNotifications(),
            menu_builder=MenuBuilder(),
            menubar=FakeMenu(),
        )

    warning_messages = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    assert sum('deprecated get_menu_class()' in message for message in warning_messages) == 1


def test_get_event_handlers_logs_and_skips_malformed_event_handler_mappings(caplog):
    class BadModern(object):
        def get_event_handlers(self):
            return ['event']

    class BadLegacy(object):
        def get_callbacks(self):
            return ['event']

    logger = logging.getLogger('test.plugins')
    manager = make_manager(logger=logger)
    manager.plugins = {
        'bad_modern': BadModern(),
        'bad_legacy': BadLegacy(),
    }

    with caplog.at_level(logging.ERROR, logger='test.plugins'):
        callbacks = manager.get_event_handlers('event')

    assert callbacks == []
    assert "bad_modern" in caplog.text
    assert "bad_legacy" in caplog.text
    assert "event handlers must be a mapping" in caplog.text


class FakeSignal(object):
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeAction(object):
    def __init__(self, name, icon=None):
        self.name = name
        self.icon = icon
        self.triggered = FakeSignal()
        self.shortcut = None
        self.checkable = None
        self.enabled = None

    def setShortcut(self, shortcut):
        self.shortcut = shortcut

    def setCheckable(self, checkable):
        self.checkable = checkable

    def setEnabled(self, enabled):
        self.enabled = enabled


class FakeMenu(object):
    def __init__(self, name='root'):
        self.name = name
        self.items = []

    def addMenu(self, name):
        menu = FakeMenu(name)
        self.items.append(('menu', menu))
        return menu

    def addAction(self, *args):
        if len(args) == 1:
            action = FakeAction(args[0])
        else:
            action = FakeAction(args[1], icon=args[0])
        self.items.append(('action', action))
        return action

    def addSeparator(self):
        self.items.append(('separator', None))


def test_menu_builder_creates_nested_menus_icons_actions_and_separators():
    root = FakeMenu()
    called = []

    def action():
        called.append(True)

    MenuBuilder(icon_factory=lambda name: 'icon:' + name).create_menu(
        root,
        {
            'name': 'Top',
            'menu_items': [
                {'name': 'Plain', 'action': action},
                {'separator': True},
                {'name': 'Icon', 'icon': 'resource', 'action': action},
            ],
        },
    )

    top = root.items[0][1]
    plain = top.items[0][1]
    icon = top.items[2][1]

    assert root.items[0][0] == 'menu'
    assert plain.name == 'Plain'
    assert plain.triggered.callbacks == [action]
    assert top.items[1] == ('separator', None)
    assert icon.name == 'Icon'
    assert icon.icon == 'icon:resource'
    assert icon.triggered.callbacks == [action]


class FakeContext(object):
    def __init__(self):
        self.items = []

    def add(self, plugin_name, contribution, data):
        self.items.append((plugin_name, contribution, data))


class BrokenContext(object):
    def add(self, plugin_name, contribution, data):
        raise RuntimeError('broken context')


def test_setup_contexts_routes_ui_and_menu_contributions():
    class Plugin(object):
        def get_ui_contributions(self):
            return [{'context': 'mdi', 'key': 'browser'}]

        def get_menu_contributions(self):
            return [{'location': 'file', 'name': 'Open'}]

    mdi_context = FakeContext()
    menu_context = FakeContext()
    data = object()
    manager = PluginManager(
        'package.plugins',
        'plugins',
        FakeConfig(),
        'app/plugins',
    )
    manager.plugins = {'plugin': Plugin(), 'legacy': object()}
    manager.register_context('mdi', mdi_context)
    manager.register_context('menus', menu_context)

    manager.setup_contexts(data)

    assert mdi_context.items == [
        ('plugin', {'context': 'mdi', 'key': 'browser'}, data),
    ]
    assert menu_context.items == [
        ('plugin', {'location': 'file', 'name': 'Open'}, data),
    ]


def test_setup_contexts_logs_and_skips_missing_unknown_and_broken_contexts(caplog):
    class MissingContext(object):
        def get_ui_contributions(self):
            return [{'key': 'browser'}]

    class UnknownContext(object):
        def get_ui_contributions(self):
            return [{'context': 'unknown', 'key': 'browser'}]

    class BrokenGetter(object):
        def get_ui_contributions(self):
            raise RuntimeError('broken getter')

    class MalformedGetter(object):
        def get_ui_contributions(self):
            return {'context': 'mdi'}

    class MalformedItem(object):
        def get_ui_contributions(self):
            return ['not a dictionary']

    class BrokenAdd(object):
        def get_ui_contributions(self):
            return [{'context': 'broken', 'key': 'browser'}]

    class MenuPlugin(object):
        def get_menu_contributions(self):
            return [{'location': 'file', 'name': 'Open'}]

    logger = logging.getLogger('test.plugins')
    manager = PluginManager(
        'package.plugins',
        'plugins',
        FakeConfig(),
        'app/plugins',
        logger=logger,
    )
    manager.plugins = {
        'missing': MissingContext(),
        'unknown': UnknownContext(),
        'broken_getter': BrokenGetter(),
        'malformed_getter': MalformedGetter(),
        'malformed_item': MalformedItem(),
        'broken_add': BrokenAdd(),
        'menu': MenuPlugin(),
    }
    manager.register_context('broken', BrokenContext())

    with caplog.at_level(logging.ERROR, logger='test.plugins'):
        manager.setup_contexts(object())

    log_text = caplog.text.lower()
    assert 'missing' in log_text
    assert 'unknown' in log_text
    assert 'broken_getter' in log_text
    assert 'malformed_getter' in log_text
    assert 'malformed_item' in log_text
    assert 'broken_add' in log_text
    assert 'menus' in log_text


def test_menu_context_renders_locations_paths_groups_order_and_action_options(caplog):
    file_menu = FakeMenu('file')
    tools_menu = FakeMenu('tools')

    def open_action():
        pass

    def heal_action():
        pass

    def save_action():
        pass

    logger = logging.getLogger('test.plugins')
    context = MenuContext(icon_factory=lambda name: 'icon:' + name, logger=logger)
    context.register_location('file', file_menu)
    context.register_location('tools', tools_menu)
    context.add(
        'plugin_b',
        {
            'location': 'file',
            'path': ('Project',),
            'group': 'open',
            'order': 20,
            'name': 'Heal',
            'action': heal_action,
        },
        {},
    )
    context.add(
        'plugin_a',
        {
            'location': 'file',
            'path': ('Project',),
            'group': 'open',
            'order': 10,
            'name': 'Open',
            'icon': 'folder',
            'shortcut': 'Ctrl+O',
            'checkable': True,
            'enabled': False,
            'action': open_action,
        },
        {},
    )
    context.add(
        'plugin_a',
        {
            'location': 'file',
            'path': ('Project',),
            'group': 'save',
            'order': 5,
            'name': 'Save',
            'action': save_action,
        },
        {},
    )
    context.add('plugin_c', {'location': 'tools', 'name': 'Tool'}, {})
    context.add('plugin_malformed', 'not a dictionary', {})
    context.add('plugin_skip', {'location': 'missing', 'name': 'Skip'}, {})

    with caplog.at_level(logging.ERROR, logger='test.plugins'):
        context.render()

    project_menu = file_menu.items[0][1]
    open_item = project_menu.items[0][1]
    heal_item = project_menu.items[1][1]
    save_item = project_menu.items[3][1]

    assert file_menu.items[0][0] == 'menu'
    assert project_menu.name == 'Project'
    assert [item[0] for item in project_menu.items] == [
        'action',
        'action',
        'separator',
        'action',
    ]
    assert [open_item.name, heal_item.name, save_item.name] == [
        'Open',
        'Heal',
        'Save',
    ]
    assert open_item.icon == 'icon:folder'
    assert open_item.shortcut == 'Ctrl+O'
    assert open_item.checkable is True
    assert open_item.enabled is False
    assert open_item.triggered.callbacks == [open_action]
    assert heal_item.triggered.callbacks == [heal_action]
    assert save_item.checkable is False
    assert save_item.enabled is True
    assert tools_menu.items[0][1].name == 'Tool'
    assert 'missing' in caplog.text.lower()
    assert 'plugin_malformed' in caplog.text

class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class ServicePlugin(BasePlugin):
    def __init__(self, services):
        super().__init__({})
        self._services = services

    def get_services(self):
        return self._services


def test_base_plugin_exposes_no_services_by_default():
    plugin = BasePlugin({})

    assert plugin.get_services() == {}


def test_collect_services_merges_base_and_plugin_services():
    logger = logging.getLogger('test.plugins.services')
    manager = make_manager(logger=logger)
    manager.plugins = {
        'alpha': ServicePlugin({'answer': 42}),
        'beta': ServicePlugin({'greeter': str.upper}),
    }

    services = manager.collect_services({'execute_command': object()})

    assert 'execute_command' in services
    assert services['answer'] == 42
    assert services['greeter'] is str.upper
    assert manager.services is services


def test_collect_services_skips_invalid_and_conflicting_entries():
    logger = logging.getLogger('test.plugins.services')
    handler = RecordingHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        manager = make_manager(logger=logger)
        manager.plugins = {
            'alpha': ServicePlugin({'shared': 'first', 'unique': 'ok'}),
            'beta': ServicePlugin({'shared': 'second'}),
            'gamma': ServicePlugin(['not', 'a', 'mapping']),
        }

        services = manager.collect_services()

        assert services['shared'] == 'first'
        assert services['unique'] == 'ok'
        messages = [record.getMessage() for record in handler.records]
        assert any('must be a mapping' in message for message in messages)
        assert any(
            'conflicts with an existing service' in message
            for message in messages
        )
    finally:
        logger.removeHandler(handler)


def test_legacy_plugin_setup_complete_runs_as_default_activity():
    calls = []
    data = {'services': object()}

    class LegacySetupPlugin(BasePlugin):
        def plugin_setup_complete(self, setup_data):
            calls.append(('legacy', setup_data))

    manager = make_manager()
    manager.plugins = {'legacy': LegacySetupPlugin({})}

    manager.setup_complete(data)

    assert calls == [('legacy', data)]


def test_duck_typed_plugin_setup_complete_still_runs():
    calls = []
    data = {'services': object()}

    class DuckTypedSetupPlugin(object):
        def plugin_setup_complete(self, setup_data):
            calls.append(('duck', setup_data))

    manager = make_manager()
    manager.plugins = {'duck': DuckTypedSetupPlugin()}

    manager.setup_complete(data)

    assert calls == [('duck', data)]


def test_multiple_setup_activities_run_in_priority_order():
    calls = []
    data = {'app': object()}

    class ActivityPlugin(BasePlugin):
        def get_setup_activities(self):
            return [
                {
                    'name': 'late',
                    'priority': DEFAULT_SETUP_PRIORITY + 10,
                    'action': self.late,
                },
                {
                    'name': 'early',
                    'priority': DEFAULT_SETUP_PRIORITY - 10,
                    'action': self.early,
                },
            ]

        def early(self, setup_data):
            calls.append(('early', setup_data))

        def late(self, setup_data):
            calls.append(('late', setup_data))

    manager = make_manager()
    manager.plugins = {'activity': ActivityPlugin({})}

    manager.setup_complete(data)

    assert calls == [('early', data), ('late', data)]


def test_setup_activity_ordering_is_deterministic_across_plugins():
    calls = []

    class NamedActivityPlugin(BasePlugin):
        def __init__(self, label):
            super().__init__({})
            self.label = label

        def get_setup_activities(self):
            return [
                {
                    'name': 'same_priority',
                    'priority': DEFAULT_SETUP_PRIORITY,
                    'action': self.record,
                },
            ]

        def record(self, data):
            del data
            calls.append(self.label)

    manager = make_manager()
    manager.plugins = {
        'zeta': NamedActivityPlugin('zeta'),
        'alpha': NamedActivityPlugin('alpha'),
    }

    manager.setup_complete({})

    assert calls == ['alpha', 'zeta']


def test_setup_activity_names_break_priority_and_plugin_ties():
    calls = []

    class TiedActivityPlugin(BasePlugin):
        def get_setup_activities(self):
            return [
                {
                    'name': 'second',
                    'priority': DEFAULT_SETUP_PRIORITY,
                    'action': self.second,
                },
                {
                    'name': 'first',
                    'priority': DEFAULT_SETUP_PRIORITY,
                    'action': self.first,
                },
            ]

        def first(self, data):
            del data
            calls.append('first')

        def second(self, data):
            del data
            calls.append('second')

    manager = make_manager()
    manager.plugins = {'plugin': TiedActivityPlugin({})}

    manager.setup_complete({})

    assert calls == ['first', 'second']


def test_no_argument_plugin_setup_complete_fallback_still_runs(caplog):
    calls = []

    class NoArgumentSetupPlugin(BasePlugin):
        def plugin_setup_complete(self):
            calls.append('legacy-no-arg')

    logger = logging.getLogger('test.plugins.setup')
    manager = make_manager(logger=logger)
    manager.plugins = {'legacy': NoArgumentSetupPlugin({})}

    with caplog.at_level(logging.WARNING, logger='test.plugins.setup'):
        manager.setup_complete({'unused': object()})

    assert calls == ['legacy-no-arg']
    assert 'using old API' in caplog.text

def _make_plugin_dirs(tmp_path, names):
    for name in names:
        (tmp_path / name).mkdir(parents=True)
    return str(tmp_path)


def test_discover_modules_ignores_config_defaults(tmp_path, caplog):
    """A config default must never be read as a plugin's enable flag."""
    config = FakeConfig(defaults={'userlib': '/some/path/userlib'})
    plugins_dir = _make_plugin_dirs(tmp_path, ['userlib'])
    logger = logging.getLogger('test.plugins.discover.defaults')
    manager = PluginManager(
        'package.plugins', plugins_dir, config, 'app/plugins',
        default_plugins=(), logger=logger,
    )

    with caplog.at_level(logging.WARNING, logger=logger.name):
        modules = manager.discover_modules()

    # Before the fix this raised ValueError: Not a boolean: /some/path/userlib
    assert modules == {}
    assert config.sections['app/plugins']['userlib'] is False
    assert 'shares its name with a config default' in caplog.text


def test_discover_modules_keeps_a_flag_set_in_both_places(tmp_path):
    """A section option shadows the default, so an explicit flag still wins."""
    config = FakeConfig(defaults={'userlib': '/some/path/userlib'})
    config.sections['app/plugins'] = {'userlib': True}
    plugins_dir = _make_plugin_dirs(tmp_path, ['userlib'])
    manager = PluginManager(
        'package.plugins', plugins_dir, config, 'app/plugins',
        default_plugins=(), logger=logging.getLogger('test.plugins.discover.both'),
    )

    manager.discover_modules()

    assert config.sections['app/plugins']['userlib'] is True


def test_discover_modules_seeds_flags_as_booleans(tmp_path):
    config = FakeConfig()
    plugins_dir = _make_plugin_dirs(tmp_path, ['enabled_one', 'disabled_one'])
    manager = PluginManager(
        'package.plugins', plugins_dir, config, 'app/plugins',
        default_plugins=('enabled_one',),
        logger=logging.getLogger('test.plugins.discover.bools'),
    )

    manager.discover_modules()

    assert config.sections['app/plugins']['enabled_one'] is True
    assert config.sections['app/plugins']['disabled_one'] is False


def test_setup_complete_runs_optional_argument_hook_once():
    """The BasePlugin signature must not be re-run by an old-API retry."""
    calls = []

    class OptionalArgumentPlugin(BasePlugin):
        def plugin_setup_complete(self, data=None):
            calls.append(data)
            raise RuntimeError('failed after the side effect')

    manager = make_manager(logger=logging.getLogger('test.plugins.setup.once'))
    manager.plugins = {'optional': OptionalArgumentPlugin({})}
    data = {'settings': object()}

    manager.setup_complete(data)

    assert calls == [data]


def test_empty_generator_contributions_do_not_report_a_missing_context():
    class GeneratorPlugin(BasePlugin):
        def get_menu_contributions(self):
            return (contribution for contribution in [])

    logger = logging.getLogger('test.plugins.contributions.generator')
    manager = make_manager(logger=logger)
    manager.plugins = {'gen': GeneratorPlugin({})}
    manager.contexts = {}

    records = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    logger.addHandler(handler)
    try:
        manager.setup_contexts({})
    finally:
        logger.removeHandler(handler)

    assert not [message for message in records if 'menus' in message]


def test_menu_context_group_order_is_independent_of_discovery_order():
    def render_with(order):
        menu = _RecordingMenu()
        context = MenuContext(logger=logging.getLogger('test.plugins.menus.order'))
        context.register_location('file', menu)
        for plugin_name, group, name in order:
            context.add(
                plugin_name,
                {'location': 'file', 'group': group, 'name': name},
                {},
            )
        context.render()
        return menu.entries

    order = [('zeta', 'beta', 'Z'), ('alpha', 'alpha', 'A'), ('mid', None, 'M')]
    assert render_with(order) == render_with(list(reversed(order)))


def test_menu_context_render_is_idempotent():
    menu = _RecordingMenu()
    context = MenuContext(logger=logging.getLogger('test.plugins.menus.idempotent'))
    context.register_location('file', menu)
    context.add('one', {'location': 'file', 'name': 'A'}, {})

    context.render()
    entries_after_first = list(menu.entries)
    context.render()

    assert menu.entries == entries_after_first


class _RecordingAction(object):
    def __init__(self):
        self.triggered = SimpleNamespace(connect=lambda callback: None)

    def setShortcut(self, shortcut):
        pass

    def setCheckable(self, checkable):
        pass

    def setEnabled(self, enabled):
        pass


class _RecordingMenu(object):
    def __init__(self):
        self.entries = []

    def addAction(self, *args):
        self.entries.append(args[-1])
        return _RecordingAction()

    def addSeparator(self):
        self.entries.append('---')

    def addMenu(self, name):
        self.entries.append(('submenu', name))
        return _RecordingMenu()
