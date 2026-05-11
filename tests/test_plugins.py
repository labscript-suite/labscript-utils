import logging
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "labscript_utils" / "plugins.py"
SPEC = importlib.util.spec_from_file_location("labscript_utils.plugins", MODULE_PATH)
plugins_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(plugins_module)

BasePlugin = plugins_module.BasePlugin
PluginManager = plugins_module.PluginManager
DEFAULT_SETUP_PRIORITY = plugins_module.DEFAULT_SETUP_PRIORITY


class DummyConfig:
    def has_section(self, section):
        del section
        return True

    def add_section(self, section):
        del section

    def items(self, section):
        del section
        return []

    def set(self, section, name, value):
        del section, name, value

    def getboolean(self, section, name):
        del section, name
        return False


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


class TestPluginServices(unittest.TestCase):
    def make_manager(self):
        logger = logging.getLogger("labscript_utils.plugins.tests")
        logger.setLevel(logging.DEBUG)
        handler = RecordingHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        manager = PluginManager(
            plugin_package="unused",
            plugins_dir="unused",
            config=DummyConfig(),
            config_section="unused",
            logger=logger,
        )
        return manager, handler

    def test_base_plugin_exposes_no_services_by_default(self):
        plugin = BasePlugin({})
        self.assertEqual(plugin.get_services(), {})

    def test_collect_services_merges_base_and_plugin_services(self):
        manager, _handler = self.make_manager()
        manager.plugins = {
            "alpha": ServicePlugin({"answer": 42}),
            "beta": ServicePlugin({"greeter": str.upper}),
        }

        services = manager.collect_services({"execute_command": object()})

        self.assertIn("execute_command", services)
        self.assertEqual(services["answer"], 42)
        self.assertIs(services["greeter"], str.upper)
        self.assertIs(manager.services, services)

    def test_collect_services_skips_invalid_and_conflicting_entries(self):
        manager, handler = self.make_manager()
        manager.plugins = {
            "alpha": ServicePlugin({"shared": "first", "unique": "ok"}),
            "beta": ServicePlugin({"shared": "second"}),
            "gamma": ServicePlugin(["not", "a", "mapping"]),
        }

        services = manager.collect_services()

        self.assertEqual(services["shared"], "first")
        self.assertEqual(services["unique"], "ok")
        messages = [record.getMessage() for record in handler.records]
        self.assertTrue(any("must be a mapping" in message for message in messages))
        self.assertTrue(any("conflicts with an existing service" in message for message in messages))


class TestPluginSetupActivities(unittest.TestCase):
    def make_manager(self):
        logger = logging.getLogger("labscript_utils.plugins.setup_tests")
        logger.setLevel(logging.DEBUG)
        handler = RecordingHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        manager = PluginManager(
            plugin_package="unused",
            plugins_dir="unused",
            config=DummyConfig(),
            config_section="unused",
            logger=logger,
        )
        return manager, handler

    def test_legacy_plugin_setup_complete_runs_as_default_activity(self):
        calls = []
        data = {"services": object()}

        class LegacySetupPlugin(BasePlugin):
            def plugin_setup_complete(self, setup_data):
                calls.append(("legacy", setup_data))

        manager, _handler = self.make_manager()
        manager.plugins = {"legacy": LegacySetupPlugin({})}

        manager.setup_complete(data)

        self.assertEqual(calls, [("legacy", data)])

    def test_duck_typed_plugin_setup_complete_still_runs(self):
        calls = []
        data = {"services": object()}

        class DuckTypedSetupPlugin:
            def plugin_setup_complete(self, setup_data):
                calls.append(("duck", setup_data))

        manager, _handler = self.make_manager()
        manager.plugins = {"duck": DuckTypedSetupPlugin()}

        manager.setup_complete(data)

        self.assertEqual(calls, [("duck", data)])

    def test_multiple_setup_activities_run_in_priority_order(self):
        calls = []
        data = {"app": object()}

        class ActivityPlugin(BasePlugin):
            def get_setup_activities(self):
                return [
                    {
                        "name": "late",
                        "priority": DEFAULT_SETUP_PRIORITY + 10,
                        "action": self.late,
                    },
                    {
                        "name": "early",
                        "priority": DEFAULT_SETUP_PRIORITY - 10,
                        "action": self.early,
                    },
                ]

            def early(self, setup_data):
                calls.append(("early", setup_data))

            def late(self, setup_data):
                calls.append(("late", setup_data))

        manager, _handler = self.make_manager()
        manager.plugins = {"activity": ActivityPlugin({})}

        manager.setup_complete(data)

        self.assertEqual(calls, [("early", data), ("late", data)])

    def test_setup_activity_ordering_is_deterministic_across_plugins(self):
        calls = []

        class NamedActivityPlugin(BasePlugin):
            def __init__(self, label):
                super().__init__({})
                self.label = label

            def get_setup_activities(self):
                return [
                    {
                        "name": "same_priority",
                        "priority": DEFAULT_SETUP_PRIORITY,
                        "action": self.record,
                    },
                ]

            def record(self, data):
                del data
                calls.append(self.label)

        manager, _handler = self.make_manager()
        manager.plugins = {
            "zeta": NamedActivityPlugin("zeta"),
            "alpha": NamedActivityPlugin("alpha"),
        }

        manager.setup_complete({})

        self.assertEqual(calls, ["alpha", "zeta"])

    def test_setup_activity_names_break_priority_and_plugin_ties(self):
        calls = []

        class TiedActivityPlugin(BasePlugin):
            def get_setup_activities(self):
                return [
                    {
                        "name": "second",
                        "priority": DEFAULT_SETUP_PRIORITY,
                        "action": self.second,
                    },
                    {
                        "name": "first",
                        "priority": DEFAULT_SETUP_PRIORITY,
                        "action": self.first,
                    },
                ]

            def first(self, data):
                del data
                calls.append("first")

            def second(self, data):
                del data
                calls.append("second")

        manager, _handler = self.make_manager()
        manager.plugins = {"plugin": TiedActivityPlugin({})}

        manager.setup_complete({})

        self.assertEqual(calls, ["first", "second"])

    def test_no_argument_plugin_setup_complete_fallback_still_runs(self):
        calls = []

        class NoArgumentSetupPlugin(BasePlugin):
            def plugin_setup_complete(self):
                calls.append("legacy-no-arg")

        manager, handler = self.make_manager()
        manager.plugins = {"legacy": NoArgumentSetupPlugin({})}

        manager.setup_complete({"unused": object()})

        messages = [record.getMessage() for record in handler.records]
        self.assertEqual(calls, ["legacy-no-arg"])
        self.assertTrue(any("using old API" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
