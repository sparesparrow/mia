# Image prompts for the MIA website

Art direction and ready-to-paste prompts for replacing the site imagery in `web/assets/site/`.
The poster `your-rules.jpg` (November 2026) sets the direction: a night drive in the rain, wet asphalt,
one silver convertible, red light as the only strong colour. The older images are generic "glowing
dashboard" stock in different styles, some still show the old AI-SERVIS name, and some show features
MIA does not have (facial recognition, a "management terminal") or the wrong hardware (Raspberry Pi 5,
"12V tto 5V"). The prompts below replace them with one consistent look.

## Rules for every image

- **No text in the pixels.** Headlines, labels and UI copy go in HTML, where they can be translated, read
  by screen readers and corrected. Generators also misspell. If a screen must show something, ask for
  abstract bars, gauges or a waveform.
- **Show only what MIA does today.** Read-only OBD-II, plate log, Bluetooth/Wi-Fi scan, dashcam loop,
  voice, CD-changer audio. No face recognition, no screens that "hack" the car, no claims such as
  "production ready" (ADR-0010, REQ-WEB-002).
- **The real car and hardware.** The prototype is a 2004 Audi A4 Cabriolet (8H). Ask for a debadged grille,
  so the picture does not suggest the manufacturer endorses MIA. The hardware is a Raspberry Pi 4B,
  ESP32 dev boards, an MCP2515 CAN module and an Android phone in a dash mount.
- **Sizes.** Square 1024×1024 for the arsenal and story cards, 1536×1024 for wide images. Every image
  that becomes a link preview also needs a 1200×630 copy named `<name>-og.jpg` (see `web/README.md`).
- **Real people.** No recognisable real people, no police officers' faces, no real number plates other
  than `MIA`.

### Shared style block

Append this to every prompt:

```
cinematic night photography, rain-soaked Central European town, wet asphalt reflections,
deep black shadows, single accent colour crimson red #ff0040 with a little cold cyan, sodium street
lights, shallow depth of field, 35mm anamorphic lens, subtle film grain, high dynamic range,
photorealistic, gritty, documentary, no text, no logos, no watermark
```

### Negative prompt

```
text, letters, captions, UI labels, watermark, logo, brand badge, manufacturer emblem,
license plate other than "MIA", extra fingers, deformed hands, cartoon, 3d render, plastic skin,
oversaturated neon, purple gradient, holographic floating screens, sci-fi HUD, lens flare overload
```

## Prompts

### `hero-bg.jpg` (new hero background, 1536×1024, no text)

```
Wide establishing shot from behind and slightly above a silver 2004 convertible with the roof down,
parked alone at the edge of an empty multistorey car park roof at night, rain just stopped,
the city of Brno below with a floodlit cathedral on a hill in the far distance,
the driver's silhouette lit only by the soft glow of a phone in a dash mount,
large calm empty sky in the left half for a headline, debadged car
```

### `your-rules-clean.jpg` (the poster without baked-in text, 1536×1024)

```
A silver 2004 Audi A4 Cabriolet with the roof down and a debadged grille takes a wet bend at night,
spray from the front wheel, headlights on, number plate reading "MIA",
a floodlit gothic church on a wooded hill behind, blurred blue and red lights far behind on the road,
the left third of the frame dark and empty for a headline
```

### `anti-stalker.jpg` (1024×1024)

```
View from the driver's seat into the rear-view mirror at night in rain: the same dark hatchback
with its headlights on has followed for a while, mirror in sharp focus, the driver's eyes
reflected at the edge of the mirror, a phone in a dash mount shows a single red warning dot
```

### `covert-ops.jpg` (plate log, 1024×1024)

```
Close-up of a hand holding an Android phone in a dark car, the screen shows an abstract list of
rows with small red and white bars (no readable text), raindrops on the windscreen behind,
a tiny Raspberry Pi 4 board with a blinking green LED tucked under the seat in the background
```

### `command-center.jpg` (rename to `vignette-check.jpg`, 1024×1024)

```
Night motorway toll gantry seen through a wet windscreen, an unmarked dark estate car in the next lane,
the phone in the dash mount glows with a single abstract status indicator,
tense, observational, no people visible
```

### `tracking-map.jpg` (rename to `hands-on-wheel.jpg`, 1024×1024)

```
Driver's hands at ten and two on a leather steering wheel of a 2000s convertible at night,
thumb resting on a steering-wheel button, a phone in a dash mount shows a simple waveform,
soft red ambient light, motion blur of street lights outside
```

### `obd-voice.jpg` (1536×1024)

```
Footwell of a 2004 convertible at night, a small OBD-II plug with a short cable to a matchbox-sized
ESP32 board taped neatly under the dashboard, one green LED, the driver's knee and pedals out of focus,
warm instrument cluster glow above, macro detail, honest DIY build quality
```

### `dashcam.jpg` (1024×1024)

```
Phone in a windscreen mount recording the road ahead at night in rain, the screen shows the same
wet road with a small red recording dot, oncoming headlights smeared by the wipers,
seen from the passenger seat
```

### `investigator.jpg` (steering-wheel buttons, 1024×1024)

```
Extreme close-up of a thumb pressing a worn button on a 2000s steering wheel, the rest of the cabin
dark, the instrument cluster softly lit in red, a phone notification glow reflected on the windscreen
```

### `mobile-dj.jpg` (factory speakers, 1024×1024)

```
Open boot of a silver convertible at night, the original 6-disc CD changer bay with a small adapter
board and a neat cable plugged into its connector, a door speaker grille glowing faintly from inside
the cabin, rain on the bodywork, a portable DJ controller on the back seat
```

### `manifesto.jpg` (1024×1024)

```
A Raspberry Pi 4B and two ESP32 boards on a workbench, soldering iron, heat-shrink, a printed
OBD-II pinout pinned to the wall, a single desk lamp in a dark garage, the silver convertible's
bonnet just visible behind, the feeling of a home-built resistance workshop, no screens
```

### `neposlusnost.jpg` (new, the disobedience section, 1536×1024)

```
A small crowd of people of different ages in a dim Prague hacker space at night, laptops, a
Raspberry Pi cluster, a whiteboard with diagrams but no readable words, warm light,
a samizdat typewriter on a shelf as a nod to the parallel polis, the silver convertible parked
in the courtyard visible through a tall window, documentary style, faces turned away or blurred
```

### `pi-wiring.jpg` and `telemetry-flow.jpg`

Do not generate these. Draw them as SVG from `spec/architecture/` (Raspberry Pi 4B, MCP2515, ESP32,
OBD-II, read-only arrows), so the labels are correct and translatable.

## After generating

1. Check the image for text, logos and wrong hardware; regenerate rather than retouch.
2. Export as progressive JPEG, quality 80–85, and make the `-og.jpg` copy at 1200×630.
3. Write the `alt` text in both `web/index.html` and `web/en/index.html`.
4. Run `cd web && npm test`.
