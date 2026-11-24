# Frosted foreground over irregular cream

Release: `8d9af9fe549d210da1673764983b98722bca5325`  
Pages: [37925598686](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37925598686)  
Application version remains `e75de07cb66a`.

The owner rejected the previous Instagram cream treatment. Its green rectangular
cutouts were caused by restoring the old background inside individual text boxes.
The new edition does not use that masking path.

## Foreground and material

All copy, branding, device frames and genuine website features sit on one
continuous frosted panel. The panel uses 8% cream tint, 92% background blend,
9px blur, fine grain and a restrained rim. Its renderer accepts no text boxes,
so text position cannot create holes or opaque patches in the cream.

Editorial lettering is deep green on the existing cream palette instead of
cream text over forest. This keeps the glass lightly tinted without needing
backplates. Wording, font sizes, text placement, brand mark and genuine website
captures remain unchanged. Foreground media is composited after the glass and
is not blurred. Phones remain only on Instagram portraits01/06.

Each of the twelve images has a unique deterministic Gaussian layout:

- Four connected, irregular cream clusters, with twelve lobes between them.
  Every cluster has at least one visibly protruding lobe.
- Five separate smaller droplets, with varied radii and peaks.
- Independent Gaussian position/offset, log-radius and peak variation, plus
  twelve different orientations. Seeds preserve repeatability, not repeated layouts.

The original local cream shader still provides the dome/peak material, illumination
and contact shadows. Each source layer has seventeen primitives and nine actual
coverage groups. Transparent output reconstructs the original shader's RGB within
one level. The live website and local4174source are unchanged.

Later local-only pattern layering changes the study canvas to associated alpha.
The exporter adapter now handles that output while preserving its straight-alpha
PNG contract. All twelve exported material layers remain byte-identical; the
local background pattern is not baked into these artwork layers.
The subsequent local joined-clump model expands shader capacity to28primitives.
The exporter reads that capacity from the model while keeping its independent
seventeen-primitive poster recipes; the same twelve layer bytes are preserved.

## Evidence and delivery

Current gallery: `exports\website-launch-20261009-frosted-cream\preview.html`.
It contains six1080x1440Instagram images, six1600x1000README images, caption,
edition-specific alt text and a six-JPEG ZIP. All twelve images are replacements;
the old masked editions are preserved as rejected history. Nothing was posted
or scheduled on Instagram.

43campaign cases, nine asset cases and the README contract pass, together with
the existing72native/540pxJPEG typography checks. Thirty composition artifacts
rerender byte-identically. All twelve foreground media/text layouts match the
previous edition;25website capture-source hashes and the localstudy remain unchanged.
Two old kits'24images and two ZIPs remain intact.

The smallest orientation separation is0.4327radians (about24.8degrees); the
largest overlap between any two normalized coverage masks is0.3641. These
measurements distinguish the layouts rather than merely comparing filenames.
At least81.83%of the original material contrast remains inside the glass.
Cream changes6.14-12.71%of the final composed images and is visible on both sides.

All175live files and README/ABOUT match the commit. Only eight public paths
changed: the six showcaseJPEGs and root documents. Every runtime, stylesheet,
HTML file and other asset remains byte-identical. This is not website integration.

## Maintenance

Use new private directories, never overwrite an existing delivery:

```powershell
python .\scripts\export_campaign_cream.py --gaussian-clusters --output .local\frosted-next\layers
python .\scripts\compose_launch_campaign.py --captures .local\launch-campaign-20261008\captures\centered-labels-20261009 --frosted-cream .local\frosted-next\layers --output .local\launch-campaign-20261008\composed\frosted-next
python .\scripts\package_launch_campaign.py --source .local\launch-campaign-20261008\composed\frosted-next --output exports\frosted-next
```

Reuse captures only while their source hashes still match the website.
`--cream-backgrounds` is the rejected historical text-masked mode, not the
current default workflow. Never restore it during an artwork refresh.

Evidence: `.local\frosted-cream-launch-20261009\`, especially `layers-v2`,
`artwork-verification.json`, `parent-delivery-review.json`, `release-local.json`
and `publication.json`. `layers-v1` predates the explicit protruding-lobe guard.
Final composition: `.local\launch-campaign-20261008\composed\frosted-cream-20261009-final\`.
ZIP SHA256: `650cd445b2192128a49d17dd4d30f08318f5a385a3be559090303a9c642a9d8c`.

No new image-tool inspection or aesthetic/native-device approval is claimed.
Numerical checks do not establish the owner's visual acceptance.
