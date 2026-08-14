# Verify — 20/20 passing

- PASS — listing edges match source rows · 75 lists edges vs {'outdoors': 40, 'visit': 35} = 75
- PASS — node total = listed + our properties · 81 = 73 + 8
- PASS — every node has url · missing: none
- PASS — every node has blurb · missing: none
- PASS — every node has drive_min · missing: none
- PASS — every node has bearing · missing: none
- PASS — all edges resolve to nodes · dangling: none
- PASS — city map has real street grid · 370 streets, 98 buildings, 3 waterways
- PASS — at least 20 nodes geo-placed on the city map · 76 geo-placed (25 exact, 22 approx)
- PASS — zero external asset references in index.html · all local
- PASS — every referenced local asset exists · all present
- PASS — label contrast >= 4.5 in every palette · {'midnight': 17.02, 'dawn': 14.36, 'print': 16.88}
- PASS — total payload under 8 MB · 7248 KB
- PASS — satellite imagery + bounds exist · data/satellite.jpg + data/satellite.json
- PASS — visitors.json covers owned domains · 12 domains, 12 with data
- PASS — prospect ids unique · 42 rows, 42 unique
- PASS — prospect coords inside region · outside: none
- PASS — flagged prospect ids resolve to nodes · orphans: none
- PASS — prospects carry phone numbers · 46/64 have phones
- PASS — lock state consistent · locked, switcher stripped

Summary: 20/20 checks passing
