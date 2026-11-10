"""Regression coverage for the converter's input direction callback."""
import unittest
from unittest.mock import Mock

from ip_converter import IPConverter
from ui.gui_styles import Colors


class ConverterInputModeTests(unittest.TestCase):
    def test_switching_direction_enables_the_source_and_locks_the_result(self):
        converter = object.__new__(IPConverter)
        converter.ipv6_to_ipv4 = Mock()
        for name in (
            "ipv6_entry", "instance_combobox", "add_ipv6_button",
            "del_ipv6_button", "area_entry", "prefix_label",
        ):
            setattr(converter, name, Mock())
        converter.text_areas = {"ipv4": Mock(), "ipv6": Mock()}
        converter.process_text_area = Mock()

        for reverse in (True, False, True):
            with self.subTest(reverse=reverse):
                converter.ipv6_to_ipv4.get.return_value = reverse
                converter.ipv6_to_ipv4_mode()
                source = "ipv6" if reverse else "ipv4"
                result = "ipv4" if reverse else "ipv6"
                converter.text_areas[source].config.assert_called_with(state="normal")
                converter.text_areas[result].config.assert_called_with(state="disabled")
                converter.text_areas[source].configure.assert_called_with(bg=Colors.BG_WHITE)
                converter.text_areas[result].configure.assert_called_with(bg=Colors.BG_DISABLED)
                converter.text_areas[source].focus_set.assert_called_with()
                converter.instance_combobox.config.assert_called_with(
                    state="disabled" if reverse else "readonly"
                )
                converter.prefix_label.disable.assert_called_with(reverse)
                converter.process_text_area.assert_called_with(f"{source}_text")

    def test_reverse_conversion_accepts_common_ipv6_forms(self):
        converter = object.__new__(IPConverter)
        for address in (
            "::ffff:192.0.2.1",
            "::ffff:c000:201",
            "0000:0000:0000:0000:0000:ffff:c000:0201",
            "2001:db8::c000:201",
        ):
            with self.subTest(address=address):
                self.assertEqual(converter.ip_converse([address], "6to4"), ["192.0.2.1"])


if __name__ == "__main__":
    unittest.main()
