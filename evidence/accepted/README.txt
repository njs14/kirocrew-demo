KiroCrew endpoint control and AWS governance

Open kirocrew-aws-remote.html. It is self-contained and embeds both diagrams.
The security view now has one endpoint panel, with host protection, runtime,
policy, six numbered layers and cross-cutting controls inside it. The AWS
view and all 15 reference entries remain available in the same viewer.

Editing and reproduction (Archify revision c1443b31b496eebf4a68bf83151816c955ddb796):
1. Edit kirocrew-security-layers.architecture.json. The authoring script
   build-security-diagram.py reproduces the accepted geometry and label fixes.
2. Validate with Archify, then deliver to kirocrew-security-layers-base.html.
   Keep this accepted base unchanged.
3. Run detail-endpoint-panel.py to add detailed SVG rows and vector icons in a
   separate kirocrew-security-layers.html derivative. Check that derivative.
4. Run export-security-preview.cjs (requires sharp), also with --dark.
5. Run build-security-viewer.py to assemble the viewer and notes.
6. Review the rendered previews and viewer where a browser is available.
   Record artifact-bound findings, then use package-kirocrew-visual.py.

AWS source: kirocrew-aws-remote.architecture.json. The image-bearing derivative
is kirocrew-aws-deployment.html. AWS icons and the retained AWS preview are included.
The older add-aws-icons.cjs writes kirocrew-aws-remote.html: if regenerating AWS,
copy its output to kirocrew-aws-deployment.html before rebuilding the viewer.

Validation and limitation:
The Archify base and both displayed diagrams passed 9/9 static artifact checks.
The detailed security SVG was visually reviewed in light and dark by the author
and a subagent. See kirocrew-endpoint-review.json for findings and resolutions.
Chromium was unavailable; browser containment and interactions remain unverified.
The wrapper is a separate integration artifact, not a single-diagram deliver receipt.
Nightly source remains the verified Sept 11 build; the latest feed was not refreshed.
Source links, control limits, and demo proof are in the notes and reference tab.
