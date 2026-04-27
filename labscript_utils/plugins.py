#####################################################################
#                                                                   #
# plugins.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

"""Plugin discovery, instantiation, and callback plumbing for labscript apps.

This module is the small framework layer that labscript-suite applications use
to discover plugins, instantiate them, collect app-neutral contributions, and
ask them for callbacks at runtime. The application owns the actual settings
storage, notification manager, menu objects, UI containers, and event firing.
``PluginManager`` only calls plugin hooks and routes contributions to contexts
the application registered explicitly.

The usual package layout is::

    myapp/
        plugins/
            __init__.py
            example/
                __init__.py  # defines class Plugin

The module name becomes the plugin name. ``PluginManager`` looks for a module
attribute named ``Plugin`` and passes the saved per-plugin settings dictionary
to ``Plugin(initial_settings)``. Existing plugins do not have to inherit
``BasePlugin``; they only need to provide the same methods by duck typing.

Configuration behavior is intentionally conservative:

* Missing plugin entries are added to the config when discovered.
* Names listed in ``default_plugins`` are written as enabled by default.
* Only enabled modules are imported.
* Import or instantiation failures are logged and skipped so one broken plugin
  does not stop the application from starting.

``Callback`` and ``callback`` wrap event handlers with priority metadata.
Lower priority numbers run first. ``Callback`` behaves like a descriptor, so
decorated methods still bind to plugin instances normally when accessed through
an instance.

Two menu paths are supported, intentionally with different contracts:

* ``MenuBuilder`` is the legacy nested-dictionary renderer used by existing
  BLACS-style plugins. It consumes dictionaries with ``name``, ``menu_items``,
  ``icon``, ``action``, and ``separator`` keys and renders them immediately
  into application menu objects.
* ``MenuContext`` is the shared contribution path for future applications. It
  collects actions with explicit ``location``, ``path``, ``group``, ``order``,
  ``name``, and ``action`` metadata, then renders all plugins together after
  contribution routing is complete.

``labscript_utils.plugins`` does not know whether a plugin UI belongs in a
tab, MDI subwindow, dock widget, dialog, fixed frame, or plugin-owned modal
container. Plugins declare a named ``context`` and applications register
objects that implement ``add(plugin_name, contribution, data)``. That is the
full shared UI contract.

Minimal application integration example
---------------------------------------

The application owns plugin settings storage, concrete UI objects, and context
implementations. A compact integration with legacy settings/notifications plus
new contribution routing looks like this::

    from labscript_utils.plugins import MenuBuilder, MenuContext, PluginManager


    class App(object):
        def __init__(self, config, logger):
            self.config = config
            self.logger = logger
            self.plugin_manager = PluginManager(
                plugin_package='myapp.plugins',
                plugins_dir='/path/to/myapp/plugins',
                config=self.config,
                config_section='myapp/plugins',
                default_plugins=('example',),
                logger=self.logger,
            )

            self.plugin_manager.discover_modules()

            plugin_settings = self.load_plugin_settings()
            self.plugin_manager.instantiate_plugins(plugin_settings)

            menu_builder = MenuBuilder(icon_factory=self.icon_factory)
            settings_pages, settings_callbacks = self.plugin_manager.setup_plugins(
                data=self.app_data,
                notifications=self.notification_manager,
                menu_builder=menu_builder,
                menubar=self.menubar,
            )

            menus = MenuContext(icon_factory=self.icon_factory, logger=self.logger)
            menus.register_location('file', self.file_menu)
            menus.register_location('window', self.window_menu)

            self.plugin_manager.register_context('menus', menus)
            self.plugin_manager.register_context('mdi', MDIContext(self.mdi_area))
            self.plugin_manager.register_context(
                'dialogs',
                DialogContext(parent=self.main_window),
            )
            self.plugin_manager.setup_contexts(self.app_data)
            menus.render()

            self.settings_widget = self.build_settings_ui(settings_pages)
            for callback in settings_callbacks:
                self.register_settings_callback(callback)

            self.plugin_manager.setup_complete(self.app_data)

        def load_plugin_settings(self):
            # App-owned storage. Return a mapping from plugin name to dict.
            return {
                'example': {'enabled': True},
            }

        def build_settings_ui(self, settings_pages):
            # App-owned settings UI. Each item in settings_pages is a plugin
            # contributed settings page class.
            return settings_pages

        def register_settings_callback(self, callback):
            # App-owned settings wiring.
            self.settings_changed_callbacks.append(callback)

        def fire_event(self, name):
            # App-owned event firing. PluginManager only returns callbacks.
            for callback in self.plugin_manager.get_callbacks(name):
                callback()

        def close_plugins(self):
            self.plugin_manager.close_plugins()


Minimal plugin package example
------------------------------

This example shows the shared plugin surface. The plugin contributes a legacy
menu, a contribution-based menu action, a settings page, a notification, an MDI
window request, callbacks, ``setup_complete()`` handling, save data, and
shutdown cleanup. Methods can return empty lists or dictionaries when a feature
is not used::

    from labscript_utils.plugins import BasePlugin, callback


    class SettingsPage(object):
        pass


    class Notification(object):
        pass


    class DataBrowser(object):
        def __init__(self, parent, services):
            self.parent = parent
            self.services = services


    class Menu(object):
        def __init__(self, data):
            self.data = data

        def get_menu_items(self):
            return {
                'name': 'Example',
                'menu_items': [
                    {'name': 'Legacy Open', 'action': self.open_action},
                    {'separator': True},
                    {
                        'name': 'Legacy Settings',
                        'icon': 'gear',
                        'action': self.settings_action,
                    },
                ],
            }

        def open_action(self):
            pass

        def settings_action(self):
            pass


    class Plugin(BasePlugin):
        def __init__(self, initial_settings):
            super(Plugin, self).__init__(initial_settings)
            self.saved_state = initial_settings
            self.app_data = None

        def get_menu_class(self):
            return Menu

        def get_menu_contributions(self):
            return [
                {
                    'location': 'file',
                    'path': ('Examples',),
                    'group': 'open',
                    'order': 20,
                    'name': 'Open Data Browser',
                    'shortcut': 'Ctrl+D',
                    'icon': 'folder-open',
                    'action': self.open_data_browser,
                },
            ]

        def get_ui_contributions(self):
            return [
                {
                    'context': 'mdi',
                    'key': 'data_browser',
                    'title': 'Data Browser',
                    'factory': DataBrowser,
                },
            ]

        def get_notification_classes(self):
            return [Notification]

        def get_setting_classes(self):
            return [SettingsPage]

        def get_event_handlers(self):
            return {
                'settings_changed': self.on_settings_changed,
                'shot_complete': self.on_shot_complete,
            }

        def plugin_setup_complete(self, data):
            self.app_data = data

        def get_save_data(self):
            return {'saved_state': self.saved_state}

        def close(self):
            pass

        def open_data_browser(self):
            pass

        @callback(priority=5)
        def on_settings_changed(self):
            pass

        @callback(priority=20)
        def on_shot_complete(self):
            pass


Feature excerpts and expected UI
--------------------------------

BasePlugin subclass with saved ``initial_settings`` and ``get_save_data()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The constructor receives the per-plugin saved settings dictionary. Store it if
you need to restore state later. ``get_save_data()`` should return the
serializable data you want written back for the next application start::

    class Plugin(BasePlugin):
        def __init__(self, initial_settings):
            super(Plugin, self).__init__(initial_settings)
            self.initial_settings = initial_settings

        def get_save_data(self):
            return {
                'window_geometry': self.window_geometry,
                'last_path': self.last_path,
            }

Settings page contribution skeleton
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_setting_classes()`` returns the page classes the application should add
to its settings UI. The application owns the widget construction and storage::

    class Plugin(BasePlugin):
        def get_setting_classes(self):
            return [SettingsPage]

    class SettingsPage(object):
        pass

Expected UI result: the application shows one settings page for each returned
class, using the app's own settings shell and persistence rules.

Legacy menu skeleton with MenuBuilder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_menu_class()`` returns a class whose instance exposes
``get_menu_items()``. The nested dictionaries are translated into the app's
menu objects by ``MenuBuilder``. It expects menus and actions to support
``addMenu()``, ``addAction()``, and ``addSeparator()``::

    class Plugin(BasePlugin):
        def get_menu_class(self):
            return Menu

    class Menu(object):
        def __init__(self, data):
            self.data = data

        def get_menu_items(self):
            return {
                'name': 'Example',
                'menu_items': [
                    {'name': 'Open', 'action': self.open_action},
                    {'separator': True},
                    {
                        'name': 'Settings',
                        'icon': 'gear',
                        'action': self.settings_action,
                    },
                ],
            }

        def open_action(self):
            pass

        def settings_action(self):
            pass

Expected UI result: the app user sees a top-level menu labeled ``Example``,
with an ``Open`` action, a separator, and a ``Settings`` action. If the app
supplies ``icon_factory``, the ``Settings`` action can also show an icon.

Contribution menu skeleton with MenuContext
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_menu_contributions()`` returns dictionaries routed to the application
``menus`` context. ``MenuContext`` understands these keys:

* ``location``: app-registered top-level menu id, such as ``file`` or
  ``window``
* ``path``: optional submenu path below that location; defaults to ``()``
* ``group``: separator group within the same location/path; defaults to
  ``None``
* ``order``: numeric order within the group; defaults to ``DEFAULT_PRIORITY``
* ``name``: action text
* ``action``: callable connected to the action's ``triggered`` signal
* ``shortcut``, ``icon``, ``checkable``, and ``enabled``: optional action
  properties applied when the concrete action object supports them

File-dialog-style plugin example::

    class FileDialogsPlugin(BasePlugin):
        def __init__(self, initial_settings):
            super(FileDialogsPlugin, self).__init__(initial_settings)
            self.services = None

        def plugin_setup_complete(self, data):
            self.services = data['project_services']

        def get_menu_contributions(self):
            return [
                {
                    'location': 'file',
                    'group': 'project',
                    'order': 10,
                    'name': 'New Project',
                    'shortcut': 'Ctrl+N',
                    'action': self.new_project,
                },
                {
                    'location': 'file',
                    'group': 'project',
                    'order': 20,
                    'name': 'Open Project...',
                    'shortcut': 'Ctrl+O',
                    'action': self.open_project,
                },
                {
                    'location': 'file',
                    'group': 'save',
                    'order': 10,
                    'name': 'Save',
                    'shortcut': 'Ctrl+S',
                    'action': self.save_project,
                },
                {
                    'location': 'file',
                    'group': 'save',
                    'order': 20,
                    'name': 'Save As...',
                    'shortcut': 'Ctrl+Shift+S',
                    'action': self.save_project_as,
                },
                {
                    'location': 'file',
                    'group': 'application',
                    'order': 100,
                    'name': 'Quit',
                    'shortcut': 'Ctrl+Q',
                    'action': self.quit_application,
                },
            ]

        def new_project(self):
            self.services.new_project_dialog.open()

        def open_project(self):
            self.services.load_project_dialog.open()

        def save_project(self):
            self.services.save_project_command.execute()

        def save_project_as(self):
            self.services.save_as_project_dialog.open()

        def quit_application(self):
            self.services.quit_command.execute()

Expected UI result: the application renders the actions in its registered
``file`` menu, creates separators between the ``project``, ``save``, and
``application`` groups, and applies shortcuts without the shared framework
knowing what a project is.

App-neutral UI homing with contexts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_ui_contributions()`` returns dictionaries with a required ``context``.
The rest of the dictionary is application-defined. This is enough to support
known containers, deferred containers, and plugin-provided containers without
adding type-specific methods such as ``create_tabs()`` or
``create_mdi_windows()`` to ``PluginManager``::

    class KnownContainerContext(object):
        def __init__(self, tab_widget):
            self.tab_widget = tab_widget

        def add(self, plugin_name, contribution, data):
            widget = contribution['factory'](
                self.tab_widget,
                data['settings'][contribution['key']],
            )
            self.tab_widget.addTab(widget, contribution['title'])


    class DeferredMDIContext(object):
        def __init__(self, mdi_area):
            self.mdi_area = mdi_area
            self.openers = {}

        def add(self, plugin_name, contribution, data):
            key = contribution['key']

            def open_window():
                widget = contribution['factory'](parent=self.mdi_area, data=data)
                self.mdi_area.addSubWindow(widget)
                widget.show()
                return widget

            self.openers[key] = open_window


    class DialogContext(object):
        def __init__(self, parent):
            self.parent = parent
            self.dialogs = {}

        def add(self, plugin_name, contribution, data):
            self.dialogs[contribution['key']] = contribution['factory'](
                parent=self.parent,
                services=data['services'],
            )


    class Plugin(BasePlugin):
        def get_ui_contributions(self):
            return [
                {
                    'context': 'tabs',
                    'key': 'overview',
                    'title': 'Overview',
                    'factory': OverviewWidget,
                },
                {
                    'context': 'mdi',
                    'key': 'data_browser',
                    'title': 'Data Browser',
                    'factory': DataBrowser,
                },
                {
                    'context': 'dialogs',
                    'key': 'open_project',
                    'title': 'Open Project',
                    'factory': OpenProjectDialog,
                },
            ]

Expected UI result: each application-owned context decides how to instantiate,
store, parent, restore, defer, activate, or display its contribution. Unknown
contexts are logged and skipped by ``PluginManager.setup_contexts()``.

Notification contribution skeleton
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_notification_classes()`` returns notification classes. The application
owns the notification manager and decides how the resulting widgets are shown::

    class Plugin(BasePlugin):
        def get_notification_classes(self):
            return [Notification]

    class Notification(object):
        pass

Expected UI result: the application creates whatever notification widgets or
panels it normally uses for those classes and inserts them into its own
notification area.

Callbacks with priorities
~~~~~~~~~~~~~~~~~~~~~~~~~~

``@callback(priority=...)`` wraps a method in ``Callback`` metadata. Lower
numbers run first when the application asks ``PluginManager.get_callbacks()``::

    class SlowPlugin(BasePlugin):
        def get_event_handlers(self):
            return {
                'shot_complete': self.on_slow,
            }

        @callback(priority=20)
        def on_slow(self):
            pass

    class FastPlugin(BasePlugin):
        def get_event_handlers(self):
            return {
                'shot_complete': self.on_fast,
            }

        @callback(priority=5)
        def on_fast(self):
            pass

Expected runtime order: when the application fires ``shot_complete`` and calls
``plugin_manager.get_callbacks('shot_complete')``, the priority 5 callback
runs before the priority 20 callback, even if the plugins were discovered in a
different order.

``setup_complete()`` for app data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``setup_complete()`` is called after the application has finished startup.
Use it to access app-owned state that was not available during construction,
such as the main window, settings object, registered services, or concrete
context objects::

    class Plugin(BasePlugin):
        def plugin_setup_complete(self, data):
            self.app = data['app']
            self.settings = data['settings']
            self.services = data['services']

The ``data`` dictionary is app-defined. Old plugins may still define
``plugin_setup_complete(self)`` without the ``data`` argument, and the manager
keeps that compatibility path.

Shutdown cleanup with ``close()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``close()`` is the plugin shutdown hook. Use it to stop timers, threads,
listeners, or any other plugin-owned resources::

    class Plugin(BasePlugin):
        def close(self):
            self.worker.stop()
            self.worker.wait()

Expected behavior: the application calls each plugin's ``close()`` method
during shutdown so the plugin can release resources before exit.
"""

import importlib
import logging
import os
import warnings
from collections.abc import Mapping
from types import MethodType


DEFAULT_PRIORITY = 10

__all__ = [
    'DEFAULT_PRIORITY',
    'Callback',
    'callback',
    'BasePlugin',
    'MenuBuilder',
    'MenuContext',
    'PluginManager',
]


def _log_once(logger, seen, level, key, message):
    """Log ``message`` once for each hashable ``key``."""
    if key in seen:
        return
    seen.add(key)
    logger.log(level, message)


class Callback(object):
    """Wrap a callable with priority metadata and method-style binding.

    ``priority`` is used when ``PluginManager.get_callbacks()`` gathers all
    callbacks for a named event. Lower numbers run first.

    The descriptor protocol is implemented so that a ``Callback`` stored as a
    class attribute binds like an instance method when accessed from a plugin
    instance. This keeps decorated methods usable without extra wrapper code.
    """
    def __init__(self, func, priority=DEFAULT_PRIORITY):
        self.priority = priority
        self.func = func

    def __get__(self, instance, class_):
        """Bind to ``instance`` the same way a normal function descriptor does."""
        if instance is None:
            return self
        else:
            return MethodType(self, instance)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class callback(object):
    """Decorator that turns a function into a :class:`Callback`.

    The decorator is optional. A plain method can still be returned from
    ``get_callbacks()`` if it already behaves like a callback. Use the
    decorator when you want to attach a non-default priority or make the
    callback object explicit in the class body.
    """
    # Instantiate the decorator:
    def __init__(self, priority=DEFAULT_PRIORITY):
        self.priority = priority

    # Call the decorator
    def __call__(self, func):
        return Callback(func, self.priority)


class BasePlugin(object):
    """Reference implementation of the plugin interface.

    Subclass this when you want a concrete starting point, but it is not
    required. The manager only relies on the methods defined here; a plugin
    can also satisfy the contract by duck typing.

    ``initial_settings`` contains the saved configuration for the plugin.
    """
    def __init__(self, initial_settings):
        """Store the plugin's saved settings.

        Applications pass the dictionary returned by the previous
        ``get_save_data()`` call, or an empty dictionary for a first run.
        Subclasses commonly keep this dictionary and use it during
        ``plugin_setup_complete()`` to restore UI state or background state.
        """
        self.initial_settings = initial_settings
        self.menu = None
        self.notifications = {}

    def get_menu_class(self):
        """Return a menu class for this plugin, or ``None``.

        Deprecated compatibility hook for BLACS-style nested menus.

        The class is constructed as ``MenuClass(data)`` during
        ``PluginManager.setup_plugins()``. Its instance should provide
        ``get_menu_items()``, returning the nested menu dictionary consumed by
        :class:`MenuBuilder`. New shared plugin code should prefer
        :meth:`get_menu_contributions` instead.
        """
        return None

    def get_notification_classes(self):
        """Return notification classes contributed by this plugin.

        The application-specific notification manager constructs the
        notifications. Instances are later passed back to
        ``set_notification_instances()`` in a dictionary keyed by notification
        class.
        """
        return []

    def get_setting_classes(self):
        """Return settings-page classes contributed by this plugin.

        The application owns the settings UI and storage. The manager only
        collects these classes and returns them to the application from
        ``setup_plugins()``.
        """
        return []

    def get_event_handlers(self):
        """Return a mapping of event names to handlers, or ``None``.

        This is the preferred shared event hook surface. Return a mapping such
        as ``{'shot_complete': self.on_shot_complete}``. Event names are
        application-defined strings; this shared layer only collects,
        normalizes, and orders handlers. Values may be plain callables or
        :class:`Callback` instances created with the :class:`callback`
        decorator. The manager sorts handlers for a given event by their
        ``priority`` attribute.
        """
        return None

    def get_callbacks(self):
        """Return callbacks keyed by event name, or ``None``.

        Deprecated compatibility alias for :meth:`get_event_handlers`.

        Existing BLACS-style plugins may still override this method. New
        shared plugin code should implement :meth:`get_event_handlers`
        instead. ``BasePlugin`` routes this legacy name to the modern hook so
        the preferred surface is the real implementation path.
        """
        return self.get_event_handlers()

    def get_ui_contributions(self):
        """Return app-context UI contributions.

        Return an iterable of dictionaries. Each contribution has a
        ``context`` key naming an application-registered context. The
        application owns what that context means: a known tab area, a deferred
        MDI workspace, a dialog registry, a fixed frame, or another
        app-specific host. The remaining keys are application-defined.
        """
        return []

    def get_menu_contributions(self):
        """Return shared menu contributions.

        Return an iterable of dictionaries. This is the app-neutral menu path.
        Existing BLACS-style plugins can continue using ``get_menu_class()``
        and :class:`MenuBuilder`; new apps can register a ``menus`` context and
        route these dictionaries through :class:`MenuContext`. Apart from
        stable menu keys such as ``location``, ``path``, ``group``, ``order``,
        ``name``, and ``action``, the concrete menu objects remain
        application-owned.
        """
        return []

    def set_menu_instance(self, menu):
        """Receive the menu instance constructed for this plugin."""
        self.menu = menu

    def set_notification_instances(self, notifications):
        """Receive notification instances constructed for this plugin."""
        self.notifications = notifications

    def plugin_setup_complete(self, data=None):
        """Run after the application has finished plugin setup.

        ``data`` is an application-defined dictionary. Plugins commonly store
        references to services or state they will need later when handling
        events, building menus, or opening UI. For BLACS it contains
        references such as the main UI, experiment config, plugin mapping, and
        settings object. Older plugins may define this method without a
        ``data`` argument; ``PluginManager.setup_complete()`` keeps that
        compatibility behavior.
        """
        pass

    def get_save_data(self):
        """Return serializable plugin state for the next application start.

        The shape of this data is application-owned. Return plain data
        structures that the application can persist and pass back as
        ``initial_settings`` during the next start.
        """
        return {}

    def get_services(self):
        """Return named services exposed by this plugin.

        Return a mapping of service names to concrete objects. Applications can
        aggregate these mappings into a shared service registry before calling
        :meth:`plugin_setup_complete`, making plugin-to-plugin dependencies
        order-independent.
        """
        return {}

    def close(self):
        """Clean up resources owned by the plugin during application shutdown.

        Applications call this during shutdown. Stop timers, workers,
        listeners, or other plugin-owned resources here.
        """
        pass


class MenuBuilder(object):
    """Build menus from the nested dictionary format used by plugins.

    Each menu description is a dictionary. Supported keys are:

    * ``name``: text for a menu or action
    * ``menu_items``: child menu descriptions, making a submenu
    * ``icon``: icon name passed to ``icon_factory`` for actions
    * ``action``: callable connected to the action's ``triggered`` signal
    * ``separator``: a truthy sentinel that inserts a separator

    ``icon_factory`` is optional and should return a Qt icon object or other
    value accepted by ``addAction``. Supplying it keeps this module free of a
    direct Qt dependency.
    """
    def __init__(self, icon_factory=None):
        """Create a menu builder.

        Args:
            icon_factory (callable, optional): Function called as
                ``icon_factory(icon_name)`` before adding an icon-bearing menu
                action. Applications using Qt typically pass ``QIcon``.
        """
        self.icon_factory = icon_factory

    def create_menu(self, parent, menu_parameters):
        """Recursively build menus and actions from a nested menu dictionary."""
        if 'name' in menu_parameters:
            if 'menu_items' in menu_parameters:
                child = parent.addMenu(menu_parameters['name'])
                for child_menu_params in menu_parameters['menu_items']:
                    self.create_menu(child, child_menu_params)
            else:
                # ``icon_factory`` stays outside this module so labscript-utils
                # does not need to import a Qt binding directly.
                if 'icon' in menu_parameters and self.icon_factory is not None:
                    child = parent.addAction(
                        self.icon_factory(menu_parameters['icon']),
                        menu_parameters['name'],
                    )
                else:
                    child = parent.addAction(menu_parameters['name'])

            if 'action' in menu_parameters:
                child.triggered.connect(menu_parameters['action'])

        elif 'separator' in menu_parameters:
            parent.addSeparator()


class MenuContext(object):
    """Collect and render contribution-based menu actions.

    Applications register stable top-level menu locations, such as ``file`` or
    ``tools``. Plugins contribute action dictionaries that request a location,
    optional submenu path, separator group, order, action text, and callback.
    Rendering is deferred until all plugins have contributed so ordering and
    group separators can be computed across plugins.
    """
    def __init__(self, icon_factory=None, logger=None):
        """Create a menu context.

        Args:
            icon_factory (callable, optional): Function called as
                ``icon_factory(icon_name)`` for icon-bearing actions.
            logger (logging.Logger, optional): Logger used for skipped or
                malformed menu contributions.
        """
        self.icon_factory = icon_factory
        self.logger = logger or logging.getLogger(__name__)
        self.locations = {}
        self.contributions = []

    def register_location(self, name, menu):
        """Register an application-owned menu object as a stable location."""
        self.locations[name] = menu

    def add(self, plugin_name, contribution, data):
        """Collect one menu contribution for later rendering.

        ``data`` is accepted for the generic context contract. Menu
        contributions already contain their callbacks, so this context does not
        need to inspect app data directly.
        """
        self.contributions.append((plugin_name, contribution))

    def render(self):
        """Render all collected menu contributions into registered locations."""
        grouped = {}
        group_orders = {}

        for plugin_name, contribution in self.contributions:
            if not isinstance(contribution, dict):
                self.logger.error(
                    "Menu contribution from plugin '%s' is not a dictionary. "
                    "Skipping." % plugin_name
                )
                continue
            if 'location' not in contribution:
                self.logger.error(
                    "Menu contribution from plugin '%s' missing location. "
                    "Skipping." % plugin_name
                )
                continue
            if 'name' not in contribution:
                self.logger.error(
                    "Menu contribution from plugin '%s' missing name. "
                    "Skipping." % plugin_name
                )
                continue

            location = contribution['location']
            if location not in self.locations:
                self.logger.error(
                    "Menu contribution from plugin '%s' requested unknown "
                    "location '%s'. Skipping." % (plugin_name, location)
                )
                continue

            path = contribution.get('path', ())
            if isinstance(path, str):
                path = (path,)
            else:
                path = tuple(path)

            key = (location, path)
            group = contribution.get('group', None)
            if key not in group_orders:
                group_orders[key] = {}
            if group not in group_orders[key]:
                group_orders[key][group] = len(group_orders[key])

            grouped.setdefault(key, []).append((plugin_name, contribution))

        menus = {}
        for name, menu in self.locations.items():
            menus[(name, ())] = menu

        for key in sorted(grouped):
            location, path = key
            parent_path = ()
            for submenu_name in path:
                submenu_path = parent_path + (submenu_name,)
                submenu_key = (location, submenu_path)
                if submenu_key not in menus:
                    menus[submenu_key] = menus[(location, parent_path)].addMenu(
                        submenu_name
                    )
                parent_path = submenu_path
            menu = menus[(location, path)]

            contributions = sorted(
                grouped[key],
                key=lambda item: (
                    group_orders[key][item[1].get('group', None)],
                    item[1].get('order', DEFAULT_PRIORITY),
                    item[0],
                    item[1]['name'],
                ),
            )

            previous_group = None
            for index, (plugin_name, contribution) in enumerate(contributions):
                group = contribution.get('group', None)
                if index and group != previous_group:
                    menu.addSeparator()
                previous_group = group

                name = contribution['name']
                icon = contribution.get('icon', None)
                if icon is not None and self.icon_factory is not None:
                    action = menu.addAction(self.icon_factory(icon), name)
                else:
                    action = menu.addAction(name)

                callback = contribution.get('action', None)
                if callback is not None:
                    action.triggered.connect(callback)

                shortcut = contribution.get('shortcut', None)
                if shortcut is not None and hasattr(action, 'setShortcut'):
                    action.setShortcut(shortcut)

                checkable = contribution.get('checkable', False)
                if hasattr(action, 'setCheckable'):
                    action.setCheckable(checkable)

                enabled = contribution.get('enabled', True)
                if hasattr(action, 'setEnabled'):
                    action.setEnabled(enabled)


class PluginManager(object):
    """Manage plugin discovery, lifecycle, and callback lookup.

    The manager keeps two internal mappings:

    * ``modules``: imported plugin modules keyed by plugin name
    * ``plugins``: instantiated plugin objects keyed by plugin name

    An application normally creates one manager per plugin directory and uses
    it to discover modules, instantiate plugin objects, build UI pieces, and
    close plugins on shutdown.
    """
    def __init__(
        self,
        plugin_package,
        plugins_dir,
        config,
        config_section,
        default_plugins=(),
        logger=None,
    ):
        """Create a plugin manager.

        Args:
            plugin_package (str): Import package containing plugin subpackages,
                for example ``'myapp.plugins'``.
            plugins_dir (str): Filesystem path scanned for plugin directories.
            config: Config object with ``has_section()``, ``add_section()``,
                ``items()``, ``set()``, and ``getboolean()`` methods.
            config_section (str): Section containing plugin enable/disable
                options.
            default_plugins (iterable): Plugin names enabled by default when
                first discovered.
            logger (logging.Logger, optional): Logger used for plugin import,
                setup, callback, and shutdown errors.
        """
        self.plugin_package = plugin_package
        self.plugins_dir = plugins_dir
        self.config = config
        self.config_section = config_section
        self.default_plugins = set(default_plugins)
        self.logger = logger or logging.getLogger(__name__)
        self.modules = {}
        self.plugins = {}
        self.services = {}
        self.contexts = {}
        self._logged_plugin_warnings = set()

    def discover_modules(self):
        """Scan the plugin directory, update config defaults, and import enabled modules."""
        if not self.config.has_section(self.config_section):
            self.config.add_section(self.config_section)

        configured_plugins = set(
            name for name, val in self.config.items(self.config_section)
        )

        modules = {}
        for module_name in os.listdir(self.plugins_dir):
            module_path = os.path.join(self.plugins_dir, module_name)
            if not os.path.isdir(module_path) or module_name == '__pycache__':
                continue

            # Keep the config in sync with what is present on disk.
            if module_name not in configured_plugins:
                self.config.set(
                    self.config_section,
                    module_name,
                    str(module_name in self.default_plugins),
                )
                configured_plugins.add(module_name)

            # Only load activated plugins.
            if self.config.getboolean(self.config_section, module_name):
                try:
                    module = importlib.import_module(
                        self.plugin_package + '.' + module_name
                    )
                except Exception:
                    self.logger.exception(
                        "Could not import plugin '%s'. Skipping." % module_name
                    )
                else:
                    modules[module_name] = module

        self.modules = modules
        return modules

    def instantiate_plugins(self, plugin_settings=None):
        """Create ``Plugin`` instances for each imported module.

        ``plugin_settings`` should map plugin names to the saved configuration
        dictionary for that plugin. Missing entries fall back to an empty
        dictionary. Instantiation failures are logged and skipped.
        """
        if plugin_settings is None:
            plugin_settings = {}

        plugins = {}
        for module_name, module in self.modules.items():
            try:
                plugins[module_name] = module.Plugin(
                    plugin_settings[module_name]
                    if module_name in plugin_settings else {}
                )
            except Exception:
                self.logger.exception(
                    "Could not instantiate plugin '%s'. Skipping" % module_name
                )

        self.plugins = plugins
        return plugins

    def setup_plugins(self, data, notifications, menu_builder, menubar):
        """Collect plugin UI and startup contributions.

        This is typically called after the application has created its legacy
        menu and notification hosts and before it finishes wiring its settings
        UI and callback registrations. The method returns a tuple of
        ``(settings_pages, settings_callbacks)`` for the application to
        consume.
        """
        settings_pages = []
        settings_callbacks = []

        for module_name, plugin in self.plugins.items():
            try:
                # Setup settings page.
                settings_pages.extend(plugin.get_setting_classes())

                # Setup menu.
                menu_class = plugin.get_menu_class()
                if menu_class:
                    _log_once(
                        self.logger,
                        self._logged_plugin_warnings,
                        logging.WARNING,
                        (module_name, 'get_menu_class'),
                        "Plugin '%s' uses deprecated get_menu_class(); "
                        "prefer get_menu_contributions() instead." % module_name
                    )
                    # Must store a reference or else the methods called when
                    # the menu actions are triggered will be garbage collected.
                    menu = menu_class(data)
                    menu_builder.create_menu(menubar, menu.get_menu_items())
                    plugin.set_menu_instance(menu)

                # Setup notifications.
                plugin_notifications = {}
                for notification_class in plugin.get_notification_classes():
                    notifications.add_notification(notification_class)
                    plugin_notifications[notification_class] = (
                        notifications.get_instance(notification_class)
                    )
                plugin.set_notification_instances(plugin_notifications)

                # Register callbacks.
                callbacks = self._get_plugin_event_handlers(module_name, plugin)
                # Save the settings_changed callback in a separate list for
                # setting up later.
                if callbacks and 'settings_changed' in callbacks:
                    settings_callbacks.append(callbacks['settings_changed'])

            except Exception:
                self.logger.exception(
                    "Plugin '%s' error. Plugin may not be functional." % module_name
                )

        return settings_pages, settings_callbacks

    def register_context(self, name, context):
        """Register an application-owned plugin contribution context."""
        self.contexts[name] = context

    def _get_contributions(self, plugin, module_name, method_name, label):
        """Return a plugin contribution iterable, logging malformed results."""
        if not hasattr(plugin, method_name):
            return []

        try:
            contributions = getattr(plugin, method_name)()
        except Exception:
            self.logger.exception(
                "Error getting %s contributions from plugin '%s'. Skipping."
                % (label, module_name)
            )
            return []

        if contributions is None:
            return []

        if (
            isinstance(contributions, (dict, str, bytes))
            or not hasattr(contributions, '__iter__')
        ):
            self.logger.error(
                "Plugin '%s' %s contributions must be an iterable of "
                "dictionaries. Skipping." % (module_name, label)
            )
            return []

        return contributions

    def setup_contexts(self, data):
        """Route plugin-declared UI and menu contributions to app contexts."""
        for module_name, plugin in self.plugins.items():
            ui_contributions = self._get_contributions(
                plugin,
                module_name,
                'get_ui_contributions',
                'UI',
            )

            for contribution in ui_contributions:
                if not isinstance(contribution, dict):
                    self.logger.error(
                        "UI contribution from plugin '%s' is not a dictionary. "
                        "Skipping." % module_name
                    )
                    continue
                if 'context' not in contribution:
                    self.logger.error(
                        "UI contribution from plugin '%s' missing context. "
                        "Skipping." % module_name
                    )
                    continue

                context_name = contribution['context']
                if context_name not in self.contexts:
                    self.logger.error(
                        "UI contribution from plugin '%s' requested unknown "
                        "context '%s'. Skipping." % (module_name, context_name)
                    )
                    continue

                try:
                    self.contexts[context_name].add(module_name, contribution, data)
                except Exception:
                    self.logger.exception(
                        "Error adding UI contribution from plugin '%s' to "
                        "context '%s'. Skipping." % (module_name, context_name)
                    )

            menu_contributions = self._get_contributions(
                plugin,
                module_name,
                'get_menu_contributions',
                'menu',
            )

            if menu_contributions and 'menus' not in self.contexts:
                self.logger.error(
                    "Plugin '%s' provided menu contributions, but no 'menus' "
                    "context is registered. Skipping." % module_name
                )
                continue

            for contribution in menu_contributions:
                if not isinstance(contribution, dict):
                    self.logger.error(
                        "Menu contribution from plugin '%s' is not a "
                        "dictionary. Skipping." % module_name
                    )
                    continue
                try:
                    self.contexts['menus'].add(module_name, contribution, data)
                except Exception:
                    self.logger.exception(
                        "Error adding menu contribution from plugin '%s'. "
                        "Skipping." % module_name
                    )

    def collect_services(self, base_services=None):
        """Merge app-owned and plugin-owned services into one registry."""
        if base_services is None:
            services = {}
        elif isinstance(base_services, Mapping):
            services = dict(base_services)
        else:
            self.logger.error(
                "Base services must be a mapping. Ignoring invalid registry."
            )
            services = {}

        for module_name, plugin in self.plugins.items():
            if not hasattr(plugin, "get_services"):
                continue

            try:
                plugin_services = plugin.get_services()
            except Exception:
                self.logger.exception(
                    "Error getting services from plugin '%s'. Skipping."
                    % module_name
                )
                continue

            if plugin_services is None:
                continue
            if not isinstance(plugin_services, Mapping):
                self.logger.error(
                    "Plugin '%s' services must be a mapping. Skipping."
                    % module_name
                )
                continue

            for service_name, service in plugin_services.items():
                if service_name in services:
                    self.logger.error(
                        "Plugin '%s' service '%s' conflicts with an existing "
                        "service. Keeping the original registration."
                        % (module_name, service_name)
                    )
                    continue
                services[service_name] = service

        self.services = services
        return services

    def setup_complete(self, data):
        """Notify plugins that the application has finished startup."""
        for module_name, plugin in self.plugins.items():
            try:
                plugin.plugin_setup_complete(data)
            except Exception:
                self.logger.exception(
                    "Error in plugin_setup_complete() for plugin '%s'. "
                    "Trying again with old call signature..." % module_name
                )
                # Backwards compatibility for old plugins.
                try:
                    plugin.plugin_setup_complete()
                    self.logger.warning(
                        "Plugin '%s' using old API. Please update "
                        "Plugin.plugin_setup_complete method to accept a "
                        "dictionary of blacs_data as the only argument."
                        % module_name
                    )
                except Exception:
                    self.logger.exception(
                        "Plugin '%s' error. Plugin may not be functional."
                        % module_name
                    )

    def _defines_hook(self, plugin, method_name):
        """Return whether ``plugin`` overrides ``method_name`` meaningfully."""
        plugin_method = getattr(type(plugin), method_name, None)
        if plugin_method is None:
            return False

        base_method = getattr(BasePlugin, method_name, None)
        return plugin_method is not base_method

    def _get_plugin_event_handlers(self, module_name, plugin):
        """Return normalized event handlers for one plugin."""
        has_modern = self._defines_hook(plugin, 'get_event_handlers')
        has_legacy = self._defines_hook(plugin, 'get_callbacks')

        if has_modern:
            if has_legacy:
                _log_once(
                    self.logger,
                    self._logged_plugin_warnings,
                    logging.WARNING,
                    (module_name, 'get_callbacks'),
                    "Plugin '%s' defines deprecated get_callbacks() and "
                    "preferred get_event_handlers(); ignoring get_callbacks()."
                    % module_name
                )
            handlers = plugin.get_event_handlers()
        elif has_legacy:
            _log_once(
                self.logger,
                self._logged_plugin_warnings,
                logging.WARNING,
                (module_name, 'get_callbacks'),
                "Plugin '%s' uses deprecated get_callbacks(); "
                "implement get_event_handlers() instead." % module_name
            )
            handlers = plugin.get_callbacks()
        else:
            return None

        if handlers is None:
            return None
        if not isinstance(handlers, Mapping):
            self.logger.error(
                "Plugin '%s' event handlers must be a mapping. Skipping."
                % module_name
            )
            return None

        return handlers

    def get_event_handlers(self, name):
        """Return all event handlers registered for ``name``, sorted by priority."""
        callbacks = []

        for module_name, plugin in self.plugins.items():
            try:
                plugin_callbacks = self._get_plugin_event_handlers(
                    module_name,
                    plugin,
                )
                if plugin_callbacks and name in plugin_callbacks:
                    callbacks.append(plugin_callbacks[name])
            except Exception:
                self.logger.exception('Error getting callbacks from %s.' % str(plugin))

        callbacks.sort(
            key=lambda callback: getattr(callback, 'priority', DEFAULT_PRIORITY)
        )
        return callbacks

    def get_callbacks(self, name):
        """Deprecated compatibility wrapper for :meth:`get_event_handlers`."""
        warnings.warn(
            "PluginManager.get_callbacks() is deprecated; use "
            "PluginManager.get_event_handlers() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_event_handlers(name)

    def close_plugins(self):
        """Call ``close()`` on every plugin during application shutdown."""
        for module_name, plugin in self.plugins.items():
            try:
                plugin.close()
            except Exception as e:
                self.logger.error(
                    'Could not close plugin %s. Error was: %s'
                    % (module_name, str(e))
                )
