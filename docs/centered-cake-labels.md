# Centered cake captions

Release: `a61f3a6e63f314bfdafb184c71cfe95a8368cd6e`  
Pages: [37918633744](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37918633744)  
Asset version: `e75de07cb66a`

Every cake name is centered beneath its own photograph. The scoped rule in
`web\readability.css` sets both `width: 100%` and `text-align: center`; full width
also handles static flex-column captions that previously sized to their text.
Font sizes, other headings, Order/Enlarge controls, links and photographs are unchanged.

The local fit run covers 410 caption measurements across enhanced and static
states. Caption/image frame centres match exactly; the largest single-line text
centre difference is 0.0078125 CSS pixels. The existing 131 notebook/300 photo
matrix and full site/entrance checks pass. All fifteen static captions and four
enhanced layouts also pass on the public site with zero frame-centre difference.
131 Node, nine asset and the README contract checks pass.

All175live files and rootREADME/ABOUT match the commit. Five public paths changed:
the one caption rule, HTML cache references, the notebook showcase and root docs.
All other media, styles and JavaScript are unchanged. No website cream integration.

Current kit: `exports\website-launch-20261009-centered-labels\`. Its notebook
portraits/landscapes show the centered names with the existing cream artwork.
Only public05showcase was replaced; older kits remain intact.
ZIP SHA256: `38bcbb66456cbfbdede93cdbdcaf87017dcfb4906055fa033bd3cde4fa13f8ad`.

Evidence: `.local\center-cake-labels-20261009\`, including `publication.json`,
`public-alignment.json`, `alignment-probe.json`, `local-fit-final\review.json`,
`local-site\review.json`, `local-entry\review.json` and `parent-delivery-review.json`.
The initial reviewer assignment-scope failure remains separate from final evidence.
No image-tool views, Instagram posting or new aesthetic approval are claimed.
