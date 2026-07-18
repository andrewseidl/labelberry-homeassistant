# LabelBerry for Home Assistant

[LabelBerry](https://github.com/andrewseidl/labelberry) label-printer control from Home
Assistant. This custom integration reports printer status and adds the
`labelberry.print_label` and `labelberry.print_template` actions.

## Requirements

- Home Assistant 2026.7.0 or newer.
- A reachable LabelBerry server with the status and quick-print API enabled.
- The `/api/templates/print` endpoint is additionally required when using the
  `labelberry.print_template` action.
- A printer and fonts supported by that LabelBerry server. Unicode and emoji rendering
  depends on the server's installed fonts and the printer is monochrome.

## Install with HACS

This integration is distributed as a custom repository rather than through the default
HACS catalog.

1. Open HACS and select **Integrations**.
2. Open the menu, select **Custom repositories**, and add
   `https://github.com/andrewseidl/labelberry-homeassistant` with category
   **Integration**.
3. Find **LabelBerry** in HACS and select **Download**.
4. Restart Home Assistant.

## Configure

Go to **Settings → Devices & services → Add integration**, search for **LabelBerry**,
and enter the full HTTP or HTTPS URL of the LabelBerry server. A path prefix is allowed.
Only one server can be configured.

To change the URL later, open the LabelBerry integration's menu and select
**Reconfigure**. Home Assistant validates the new server before saving it.

## Printer status

The `sensor.labelberry_status` enum reports `connected` or `disconnected` and includes
the detected tape width and backend as attributes. A valid `disconnected` response means
the server is reachable but its printer is not connected. An unavailable entity means
Home Assistant could not obtain a valid response from the server.

## Print labels

Call `labelberry.print_label` from an automation, script, or the Developer Tools action
panel.

| Field | Required | Description |
| --- | --- | --- |
| `text` | Yes | Non-empty centered text. Newlines create separately centered lines. |
| `left` | No | Non-empty Unicode text or emoji in the left flank box. |
| `right` | No | Non-empty Unicode text or emoji in the right flank box. |
| `copies` | No | Number of copies from 1 through 100; defaults to 1. |

A plain label:

```yaml
action: labelberry.print_label
data:
  text: Pantry
```

A two-line label, with each line centered:

```yaml
action: labelberry.print_label
data:
  text: |
    Cold
    Wash
  copies: 2
```

A single label containing an emoji, two centered lines, and a different emoji:

```yaml
action: labelberry.print_label
data:
  left: "🧺"
  text: |
    Cold
    Wash
  right: "🌬️"
```

The LabelBerry renderer gives the left and right flank boxes equal widths and centers
each text line in the middle box. This keeps the middle text visually centered even when
the two flanks differ.

A successful action means the server accepted the job into its queue, not that printing
has finished.

To print a saved template with variable values:

```yaml
action: labelberry.print_template
data:
  template: Leftovers
  variables:
    food: Curry
  copies: 3
```

LabelBerry print actions are sent once and are never retried automatically.

## Troubleshooting

- If setup reports that it cannot connect, verify the URL from the Home Assistant host
  and check that the LabelBerry server is running.
- If the status is `disconnected`, check the printer connection and LabelBerry backend.
- If printing reports a render error, shorten the content, reduce the number of lines, or
  use a wider tape. The backend's error code and message are shown in Home Assistant.
- If an emoji is missing, install a font containing that glyph on the LabelBerry server.

## Development

The repository uses Python 3.14, `uv`, pytest, and Ruff:

```sh
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Runtime code uses only dependencies already bundled with Home Assistant.

## License

LabelBerry for Home Assistant is available under the [MIT License](LICENSE).
