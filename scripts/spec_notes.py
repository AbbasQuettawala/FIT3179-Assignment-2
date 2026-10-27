"""Add readable WHAT/WHY notes to valid JSON without changing chart encodings."""

CHART_TITLES = {
    "news-trust": "Trust in news from a separate survey - Horizontal bar chart",
    "hero-waffle": "How common is online video? - Waffle chart",
    "media-horizon": "Changes in weekly viewing - Horizon chart",
    "streaming-fta-connected": "Streaming versus free-to-air TV over time - Connected scatterplot",
    "age-media-heatmap": "Video services by age - Heatmap",
    "age-parallel-profile": "Media habits across age groups - Connected profile chart",
    "video-hours-bullet": "Viewing hours by age and format - Bullet chart",
    "video-service-bump": "Video-service rankings over time - Bump chart",
    "device-slope": "Changes in devices used for viewing - Slope chart",
    "audio-age-heatmap": "Audio formats by age - Heatmap",
    "audio-location-network": "Audio formats and listening locations - Network diagram",
    "news-age": "Online news use by age - Dot plot",
    "adii-choropleth": "Digital inclusion by state - Choropleth map",
    "adii-cartogram": "Population and digital inclusion - Dorling cartogram",
    "metro-regional": "City versus regional media habits - Dumbbell chart",
    "radio-symbol-map": "Digital-radio sites and licence counts - Proportional-symbol map",
    "radio-dot-map": "AM/FM radio-site locations - Point-location dot map",
}

CHART_NOTES = {
    "news-trust": ["Compare three news-trust percentages using horizontal bars.", "One shared 0-100 scale makes the gaps visible without separate coloured statistic cards.", "Filter the existing news indicators CSV to Trust rows. These 2026 findings come from a different survey than the ACMA age chart and must not be joined to it."],
    "hero-waffle": ["Waffle chart: one tile represents one in 100 adults.","A 100-tile grid makes the rounded share easy to picture, rather than presenting only a large number.","The source percentage was read by Python when this specification was generated. These are illustrative tiles, not 100 individual survey records."],
    "media-horizon": ["Horizon chart: layered area bands show change from the first year of each series.","Folding change into 10-point bands lets several trends fit into separate compact rows.","Python already calculated current percentage minus starting percentage and the band heights. Vega-Lite does not normalise the source here. Short-form video starts later than the other series."],
    "streaming-fta-connected": ["Connected scatterplot: x is paid streaming use, y is free-to-air use, and the path follows years.","This shows how two measurements move together over time without using two unrelated vertical scales.","These are national survey percentages, not tracked individuals. The path cannot prove that the same people switched services."],
    "age-media-heatmap": ["Video-service heatmap: columns are age groups, rows are services, colour is percentage.","A grid makes many age-by-service comparisons easier to scan than dozens of separate charts.","The CSV already contains percentages. A 0-100 colour domain is a display scale, not a normalisation calculation. People can use multiple services."],
    "age-parallel-profile": ["Connected age profiles: each age group's line links its values across media activities.","Following one coloured line reveals the media mix for an age group; hover and pin help compare groups.","Activities are categories, not continuous time. Connecting them helps comparison but does not imply measurements between activities."],
    "video-hours-bullet": ["Bullet chart: bars show age-group viewing hours; ticks show the national average for the selected format.","A shared reference tick makes it easy to see which groups watch more or less than the national average.","The dropdown filters formats, not people. The hours axis rescales by format. Hours and percentages are different measurements."],
    "video-service-bump": ["Bump chart: each service's line follows its rank through the years.","Rank makes changes in relative popularity easy to follow; direct endpoint labels identify services.","The window/rank transform computes rankings within each year. Ranking is not normalisation and does not show the size of percentage gaps."],
    "device-slope": ["Slope chart: each device connects its usage percentage in two years.","The direction and steepness of each slope help compare increases and decreases.","People can use more than one device, so percentages need not sum to 100. These are usage shares, not time spent."],
    "audio-age-heatmap": ["Audio heatmap: columns are age groups, rows are audio formats, colour is weekly listening percentage.","The grid reveals age patterns, while a second text layer supplies exact rounded readings.","The data already contains percentages. The colour domain does not normalise it. The time window differs from the video-service heatmap."],
    "audio-location-network": ["Listening network: left nodes are audio formats, right nodes are locations, and link thickness is percentage.","Links make format-to-location relationships visible; thickness expresses the strength of each relationship.","Each percentage uses listeners of that format as its base. Locations can overlap. This is not a Sankey with conserved flows, and thickness is not total audience size."],
    "news-age": ["News dot plot: each dot shows online news and information use for one age group.","Aligned positions make small differences easier to compare than differently sized areas.","The separate trust bar chart uses another survey; its data is not joined to this age chart."],
    "adii-choropleth": ["Choropleth: state shapes are coloured by digital inclusion score.","Keeping geographic outlines supports regional comparison and helps viewers locate familiar states.","Scores are already published index values, not percentages or population totals. Large states attract more visual attention because of their land area."],
    "adii-cartogram": ["Dorling cartogram: circle area represents population and colour represents inclusion score.","Replacing land area with population reduces the visual dominance of large, sparsely populated states.","Python prepared circle radii and non-overlapping positions. These transforms fit that layout to the display; they do not create inclusion scores. Size and colour refer to different years."],
    "metro-regional": ["Dumbbell chart: two points per activity compare city and regional use, joined by a rule.","The connecting segment makes the direction and size of the city-regional difference visible.","The fold transform reshapes columns into rows. It does not normalise percentages, which were prepared before loading."],
    "radio-symbol-map": ["Proportional-symbol map: circles show digital-radio sites, with area proportional to licence-record count.","Location shows the distribution and circle size reveals sites with more records.","Circle size does not represent reception range or audience. Python grouped issued licence records by site before this chart loaded."],
    "radio-dot-map": ["Point-location dot map: one equal-sized dot per AM/FM site, coloured by technology.","Equal-sized dots make site distribution the main message; colour distinguishes AM, FM and combined sites.","Dots use recorded locations, not randomly placed dot-density symbols. A dot is a licensed site, not a listener or a reception-coverage area."],
}

LAYER_NOTES = {
    "news-trust": [
        ["Draw bars on a shared 0-100 percentage scale.", "Common colour and a zero baseline make lengths directly comparable."],
        ["Write each category above its bar.", "Direct labels remain readable on narrow screens without a colour legend."],
        ["Place the exact percentage beside each bar.", "Readers can see the values without hovering or estimating from the axis."],
    ],
    "hero-waffle": [
        ["Draw the 100 rectangles.","One visual unit per percentage point makes the rounded share concrete."],
        ["Overlay a small play triangle on used-video tiles only.","The symbol connects the tiles to video without changing their numerical meaning."],
        ["Draw the headline count as chart text.","Readers get the overall figure before inspecting individual tiles."],
        ["Draw the time-window explanation.","The figure should not be mistaken for daily or weekly viewing."],
    ],
    "media-horizon": [
        ["Draw the first 10-point band.","It provides the base band before higher changes are folded over it."],
        ["Draw the second 10-point band.","A darker band indicates change beyond the first ten points."],
        ["Draw the third 10-point band.","Higher changes fit in the same compact row."],
        ["Draw the fourth 10-point band.","The largest changes remain visible without making every row taller."],
        ["Draw invisible hover rectangles around each year.","A wider invisible target makes narrow bands easier to inspect; the values do not change."],
        ["Label the final change and baseline year.","Readers can interpret the folded bands without estimating the final total."],
    ],
    "streaming-fta-connected": [
        ["Connect yearly observations in time order.","The path shows the sequence rather than implying x position determines time."],
        ["Draw one circle per year.","Individual observations remain visible along the path."],
        ["Label the first and last years.","Endpoints explain the direction of time without labelling every point."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "age-media-heatmap": [
        ["Draw the coloured cells.","Colour reveals broad patterns across rows and columns."],
        ["Draw numbers over the cells at the same x/y positions.","Readers can read exact rounded values instead of guessing from colour."],
    ],
    "age-parallel-profile": [
        ["Draw a coloured line and point markers for each age group.","Connecting category values helps the viewer follow a group's media profile."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "video-hours-bullet": [
        ["Draw age-group average hours as horizontal bars.","Length on a common baseline makes ages easy to compare."],
        ["Overlay a short vertical tick at the national average on each row.","The repeated reference makes above/below-average comparisons local and immediate."],
        ["Label each age group's hours.","Exact readings complement the visual bar lengths."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "video-service-bump": [
        ["Connect each service's yearly ranks.","The path shows whether the service moved up or down relative to the others."],
        ["Label services at the final year.","Direct labels reduce repeated trips between a line and its legend."],
    ],
    "device-slope": [
        ["Connect each device's two yearly values.","Slopes reveal the direction and size of change."],
        ["Mark each endpoint.","The actual measurements are visible rather than only the connecting line."],
        ["Label the latest device values.","Readers can identify each series and its final percentage directly."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "audio-age-heatmap": [
        ["Draw the coloured cells.","Colour reveals broad patterns across rows and columns."],
        ["Draw numbers over the cells at the same x/y positions.","Readers can read exact rounded values instead of guessing from colour."],
    ],
    "audio-location-network": [
        ["Draw a rule from each audio-format node to a location node.","Line thickness communicates the percentage for that specific relationship."],
        ["Draw audio-format nodes on the left.","They give each group of links a clear starting point."],
        ["Label the audio-format nodes.","Readers should not have to memorise colours."],
        ["Draw location nodes on the right.","Shared destinations make it easier to compare listening contexts."],
        ["Label the location nodes.","The destinations are understandable without a separate key."],
        ["Show percentages for the hovered format, or the pinned format if nothing is hovered.","The active comparison can be read precisely without showing every number at once."],
    ],
    "news-age": [
        ["Draw one dot per age group.","Position along a shared percentage axis supports comparison."],
        ["Label each dot's percentage.","Small differences can be read precisely."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "adii-choropleth": [
        ["Draw and colour state polygons after the score lookup.","The map connects inclusion scores with recognisable places."],
        ["Draw a pointer from the ACT to its offset label.","The ACT is too small to label clearly inside its boundary at national scale."],
        ["Draw a light outline behind state-label text.","The halo separates labels from coloured areas and underlying symbols."],
        ["Draw readable state abbreviations.","Viewers can identify locations without relying on shape recognition alone."],
    ],
    "adii-cartogram": [
        ["Draw the prepared state population circles.","Area encodes population while colour independently encodes inclusion."],
        ["Label each population circle with its state.","The circle layout no longer has familiar state outlines."],
        ["Draw the one-million-person reference circle.","A same-scale reference explains the meaning of circle areas."],
        ["Label the population-size reference and its date.","The viewer knows both the unit and the population vintage."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "metro-regional": [
        ["Connect the city and regional values with a rule.","The segment length reveals the size of the gap."],
        ["Draw distinct city and regional points.","Colour and shape identify the groups even when their positions are close."],
        ["Draw a short solid rule from the highlighted point towards the annotation box.","A nearby connector links the explanation to its evidence without crossing the whole chart."],
        ["Draw a pale rectangle behind the annotation.","The note stays readable over marks and grid lines."],
        ["Place a small outlined marker at the selected data point.","It identifies exactly which observation the explanation refers to."],
        ["Draw the explanatory annotation.","It explains why the highlighted pattern matters, rather than just repeating a value."],
    ],
    "radio-symbol-map": [
        ["Draw a muted state-boundary background.","It provides geographic context without competing with site circles."],
        ["Draw a circle at each digital-radio site and scale its area by licence count.","Both location and records per site can be compared."],
        ["Draw a pointer from the ACT to its offset label.","The ACT is too small to label clearly inside its boundary at national scale."],
        ["Draw a light outline behind state-label text.","The halo separates labels from coloured areas and underlying symbols."],
        ["Draw readable state abbreviations.","Viewers can identify locations without relying on shape recognition alone."],
        ["Draw the name of the selected city when zoomed in.","It preserves geographic context after the national outline leaves the viewport."],
    ],
    "radio-dot-map": [
        ["Draw a muted state-boundary background.","It provides context for the site distribution."],
        ["Draw an equal-sized dot for each AM/FM site.","Counts are represented by the number of dots, not their individual sizes."],
        ["Draw a pointer from the ACT to its offset label.","The ACT is too small to label clearly inside its boundary at national scale."],
        ["Draw a light outline behind state-label text.","The halo separates labels from coloured areas and underlying symbols."],
        ["Draw readable state abbreviations.","Viewers can identify locations without relying on shape recognition alone."],
        ["Draw the name of the selected city when zoomed in.","It preserves geographic context after the national outline leaves the viewport."],
    ],
}

FEATURE_NOTES = {
    "data": ("Load a table, geographic file or inline records.", "Keep source measurements separate from the instructions that draw them."),
    "parse": ("Read the listed CSV columns as numbers.", "Numerical comparisons and calculations must not treat values as text."),
    "sequence": ("Generate rows from start up to, but not including, stop.", "The waffle needs 100 illustrative tiles, not 100 individual survey responses."),
    "mark": ("Choose the graphical shape: rectangle, line, point, text, rule, tick, bar or geoshape.", "The mark should support the comparison this chart is designed to show."),
    "encoding": ("Map data fields to position, colour, size, text and other visual properties.", "The viewer needs a consistent visual meaning for each measurement or category."),
    "layer": ("Draw several sets of marks in the same plot.", "This combines data marks with labels, reference ticks and explanatory annotations."),
    "field": ("Read a named column from each data row.", "This connects the source data or a derived field to the visual property."),
    "domain": ("Set the input bounds or categories of a scale.", "This controls the display mapping; a domain of 0-100 does NOT normalise the data."),
    "range": ("Set the visual outputs of a scale, such as colours or symbol sizes.", "The domain's values need corresponding visual appearances."),
    "tooltip": ("List the fields shown when pointing at a mark.", "Exact values and context are available without permanently crowding the plot."),
    "sort": ("Set an explicit category or calculation order.", "Ages, services and years should not depend on accidental file order."),
    "condition": ("Use one visual setting when a test is true and another otherwise.", "This provides highlighting, readable text contrast and responsive annotations without changing measurements."),
    "params": ("Store adjustable values such as videoFormat or hoveredSeries.", "Controls and JavaScript can update the view without modifying the CSV."),
    "bind": ("Connect a parameter to an input, such as a select dropdown.", "Readers can choose a format, series or city without editing code."),
    "filter": ("Keep only rows whose expression is true; datum means the current row.", "The selected format or annotation needs a subset of the data, not a change to its values."),
    "calculate": ("Evaluate an expression and store its result under the name in as.", "Derived coordinates and labels prepare data for display without replacing source fields."),
    "window": ("Calculate ranks or row numbers across sorted rows.", "Rank compares services within each year; row_number selects an observation for a callout. Neither is normalisation."),
    "groupby": ("Run the calculation separately for each group.", "Yearly service ranks must compare services within the same year."),
    "fold": ("Turn metro and regional columns into region/value rows.", "One point layer can then draw both groups. This reshapes data; it does not normalise it."),
    "lookup": ("Join records using matching state names.", "Geographic boundaries need scores from the separate inclusion CSV to be coloured."),
    "projection": ("Convert geographic coordinates to a flat map using a conic equal-area projection.", "The Australian map preserves relative geographic areas, though not all shapes or distances."),
    "expr": ("Evaluate a dynamic expression instead of using a fixed literal.", "Coordinates, sizes or scales can respond to chart dimensions and parameter choices."),
    "format": ("Choose file parsing or numeric display formatting, depending on its location.", "For labels, .0f shows whole numbers and .1f one decimal; this does not replace the stored value."),
    "config": ("Set shared fonts, axes, legends and background styling.", "Consistent presentation keeps attention on the data rather than unnecessary decoration."),
}


# WHAT: Find which features actually occur in a specification.
# WHY: Each chart should explain its own code, not unrelated functionality.
def used_features(node):
    features = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key != "usermeta":
                features.add(key)
                features.update(used_features(value))
    elif isinstance(node, list):
        for value in node:
            features.update(used_features(value))
    return features


# WHAT: Add supported descriptions and custom usermeta explanations.
# WHY: JSON cannot contain // comments; these notes remain visible in View Source
# without making the specification invalid or changing data/mark encodings.
def add_spec_notes(name, spec, number):
    what, why, preparation = CHART_NOTES[name]
    features = used_features(spec)
    explanations = {
        "READ_ME": "These are explanatory notes, not rendering instructions. Search WHAT or WHY. The chart code follows below.",
        "chart_number": number,
        "source_file": f"specs/{number}.{name.replace('-', '_')}.json",
        "WHAT": what,
        "WHY": why,
        "data_preparation_and_limits": preparation,
        "features": {
            feature: {"WHAT": notes[0], "WHY": notes[1]}
            for feature, notes in FEATURE_NOTES.items() if feature in features
        },
    }
    if "params" in features:
        explanations["interaction_bridge"] = (
            "bind creates chart dropdowns. assets/main.js handles custom hover/click "
            "events and updates Vega signals; conditions then change appearance. "
            "The page's state selector is HTML/JavaScript; the ocean-and-amber theme is fixed."
        )
    if any(layer.get("name") == "callout_leader" for layer in spec["layer"]):
        explanations["annotation_connectors"] = (
            "The rule layer uses x/y and x2/y2 as endpoints. Current connectors are "
            "short and solid. The earlier strokeDash [3,3] meant 3 pixels of stroke "
            "followed by 3 pixels of gap. Compact mode uses the main explanation below the plot."
        )
    spec.setdefault("usermeta", {})["explanations"] = explanations
    spec["description"] = f"{number}. {CHART_TITLES[name]}"
    for layer, notes in zip(spec["layer"], LAYER_NOTES[name], strict=True):
        layer["description"] = f"WHAT: {notes[0]} WHY: {notes[1]}"
    return {
        "$schema": spec["$schema"],
        "description": spec["description"],
        "usermeta": spec["usermeta"],
        **spec,
    }
