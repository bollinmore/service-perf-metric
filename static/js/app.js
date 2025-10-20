(() => {
  if (!window.React || !window.ReactDOM) {
    console.error("React or ReactDOM is missing.");
    return;
  }
  const htmLib = window.htm;
  if (!htmLib || typeof htmLib.bind !== "function") {
    console.error("htm templating helper is missing.");
    return;
  }

  const { useState, useEffect, useMemo, useCallback, useRef } = React;
  const html = htmLib.bind(React.createElement);

  const VIEWS = [
    { id: "analytics", label: "Analytics", icon: "\u{1F4CA}" },
    { id: "reports", label: "CSV Viewer", icon: "\u{1F4C4}" },
    { id: "compare", label: "Compare", icon: "\u2696" },
  ];

  const MISSING_VALUE = "N/A";

  const formatNumber = (value, digits = 1) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return MISSING_VALUE;
    }
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: digits,
      minimumFractionDigits: 0,
    });
  };

  const formatMs = (value) => `${formatNumber(value, 1)} ms`;

  const formatPct = (value) => `${formatNumber(value, 1)}%`;

  const classNames = (...names) => names.filter(Boolean).join(' ');


  const PlotlyChart = ({ figure }) => {
    const ref = useRef(null);
    useEffect(() => {
      const node = ref.current;
      if (!node || !window.Plotly) {
        return undefined;
      }
      const data = Array.isArray(figure?.data) ? figure.data : [];
      const layout = { margin: { t: 50, r: 30, b: 70, l: 60 }, ...figure?.layout };
      window.Plotly.react(node, data, layout, {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["lasso2d", "select2d"],
      });
      return () => {
        if (window.Plotly && node) {
          window.Plotly.purge(node);
        }
      };
    }, [figure]);
    return html`<div ref=${ref} className="h-full w-full"></div>`;
  };

  const ChartCard = ({
    title,
    subtitle,
    hasData,
    onExpand,
    actions,
    renderChildrenWhenEmpty = false,
    messageWhenEmpty,
    children,
  }) =>
    html`<section
      className="flex min-h-[420px] flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm"
    >
      <div
        className="flex items-start justify-between gap-3 border-b border-gray-200 px-5 py-4"
      >
        <div>
          <h2 className="text-base font-semibold text-gray-900">${title}</h2>
          ${subtitle
            ? html`<p className="text-sm text-gray-500">${subtitle}</p>`
            : null}
        </div>
        ${actions
          ? actions
          : onExpand && hasData
          ? html`<button
                type="button"
                className="rounded-md border border-gray-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600 shadow-sm transition hover:border-indigo-400 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                onClick=${onExpand}
              >
                Expand
              </button>`
          : null}
      </div>
      <div className="flex-1 px-5 py-4">
        ${hasData || renderChildrenWhenEmpty
          ? html`<div className="h-full w-full">${children}</div>`
          : html`<div
              className="flex h-full items-center justify-center text-sm text-gray-500"
            >
              ${messageWhenEmpty || "No data available for this section."}
            </div>`}
      </div>
    </section>`;

const AnalyticsPanel = ({ state, version, onVersionChange }) => {
  const [expandedCard, setExpandedCard] = useState(null);

  useEffect(() => {
    if (!expandedCard) {
      return undefined;
    }
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setExpandedCard(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [expandedCard]);

  const lineFigure = state.lineFigure || { data: [], layout: {} };
  const barFigure = state.barFigure || { data: [], layout: {} };
  const hasLineData = Array.isArray(lineFigure.data) && lineFigure.data.length > 0;
  const hasBarData = Array.isArray(barFigure.data) && barFigure.data.length > 0;
  const currentBoxFigure =
    (state.boxFigures && state.boxFigures[version]) || { data: [], layout: {} };
  const hasBoxData = Array.isArray(currentBoxFigure.data) && currentBoxFigure.data.length > 0;
  const stats = state.versionStats || {};
  const statsVersions = stats.versions || [];
  const statsRows = stats.rows || [];
  const hasStatsData = statsVersions.length > 0 && statsRows.length > 0;

  const versionSelector =
    state.boxVersions?.length || state.versions?.length
      ? html`<label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">Version</span>
          <select
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            value=${version}
            onChange=${(event) => onVersionChange(event.target.value)}
          >
            ${(state.boxVersions || state.versions || []).map(
              (opt) =>
                html`<option key=${`box-${opt}`} value=${opt}>${opt}</option>`
            )}
          </select>
        </label>`
      : null;

  const statsCardContent = html`<div className="overflow-auto">
    <table className="min-w-full divide-y divide-gray-200 text-sm">
      <thead className="bg-gray-50">
        <tr>
          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
            Metric
          </th>
          ${statsVersions.map(
            (col) =>
              html`<th
                key=${`stat-${col}`}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600"
              >
                ${col}
              </th>`
          )}
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100 bg-white">
        ${statsRows.map(
          (row) =>
            html`<tr key=${row.metric}>
              <td className="whitespace-nowrap px-4 py-2 font-medium text-gray-700">
                ${row.metric}
              </td>
              ${statsVersions.map(
                (col) =>
                  html`<td
                    key=${`${row.metric}-${col}`}
                    className="whitespace-nowrap px-4 py-2 text-gray-700"
                  >
                    ${formatMs(row.values?.[col])}
                  </td>`
              )}
            </tr>`
        )}
      </tbody>
    </table>
  </div>`;

  const analyticsCards = [
    html`<${ChartCard}
      key="line"
      title="Average Loading Time per Service (by Version)"
      hasData=${hasLineData}
      onExpand=${hasLineData ? () => setExpandedCard("line") : null}
      messageWhenEmpty="No data available for this chart."
    >
      <${PlotlyChart} figure=${lineFigure} />
    </${ChartCard}>`,
    html`<${ChartCard}
      key="bar"
      title="Average Loading Time per Service (Grouped Bar)"
      hasData=${hasBarData}
      messageWhenEmpty=${state.datasetError || "No data available for this chart."}
      onExpand=${hasBarData ? () => setExpandedCard("bar") : null}
    >
      <${PlotlyChart} figure=${barFigure} />
    </${ChartCard}>`,
    html`<${ChartCard}
      key="distribution"
      title="Service Loading Time Distribution"
      subtitle="Inspect service distributions for a specific version."
      hasData=${hasBoxData}
      renderChildrenWhenEmpty=${true}
      messageWhenEmpty="No distribution data available for this version."
      actions=${html`<div className="flex items-center gap-2">
        ${versionSelector}
        ${hasBoxData
          ? html`<button
              type="button"
              className="rounded-md border border-gray-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600 shadow-sm transition hover:border-indigo-400 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              onClick=${() => setExpandedCard("distribution")}
            >
              Expand
            </button>`
          : null}
      </div>`}
      onExpand=${null}
    >
      <div className="h-full">
        ${hasBoxData
          ? html`<${PlotlyChart} figure=${currentBoxFigure} />`
          : html`<div className="flex h-full items-center justify-center text-sm text-gray-500">
              No distribution data available for this version.
            </div>`}
      </div>
    </${ChartCard}>`,
    html`<${ChartCard}
      key="stats"
      title="Version Summary Statistics"
      hasData=${hasStatsData}
      onExpand=${hasStatsData ? () => setExpandedCard("stats") : null}
      messageWhenEmpty="No summary statistics available."
    >
      ${statsCardContent}
    </${ChartCard}>`,
  ];

  const overlay = expandedCard
    ? html`<div
        className="fixed inset-0 z-50 flex flex-col bg-black/60"
        role="dialog"
        aria-modal="true"
        onClick=${(event) => {
          if (event.target === event.currentTarget) {
            setExpandedCard(null);
          }
        }}
      >
        <div className="flex h-full w-full flex-col bg-white">
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">
              ${expandedCard === "line"
                ? "Average Loading Time per Service (by Version)"
                : expandedCard === "bar"
                ? "Average Loading Time per Service (Grouped Bar)"
                : expandedCard === "distribution"
                ? "Service Loading Time Distribution"
                : "Version Summary Statistics"}
            </h2>
            <button
              type="button"
              className="rounded-md border border-gray-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600 transition hover:border-indigo-400 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              onClick=${() => setExpandedCard(null)}
            >
              Close
            </button>
          </div>
          <div className="flex-1 min-h-[400px] overflow-hidden p-6">
            ${expandedCard === "line" || expandedCard === "bar"
              ? html`<${PlotlyChart}
                  figure=${expandedCard === "line" ? lineFigure : barFigure}
                />`
              : expandedCard === "distribution"
              ? html`<${PlotlyChart} figure=${currentBoxFigure} />`
              : statsCardContent}
          </div>
        </div>
      </div>`
    : null;

  return html`<div className="space-y-6">
    ${(state.datasetWarnings?.length || state.datasetError)
      ? html`<div className="space-y-2">
          ${(state.datasetWarnings || []).map(
            (warning, idx) =>
              html`<div
                key=${`warn-${idx}`}
                className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
              >
                ${warning}
              </div>`
          )}
          ${state.datasetError
            ? html`<div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
                ${state.datasetError}
              </div>`
            : null}
        </div>`
      : null}
    <div className="grid gap-6 lg:grid-cols-2">
      ${analyticsCards}
    </div>
    ${overlay}
  </div>`;
  };

  const App = ({ initial }) => {
    const searchParams = useMemo(
      () => new URLSearchParams(window.location.search),
      []
    );
    const datasetParam = searchParams.get("dataset") || "";
    const viewParam = searchParams.get("view") || "analytics";
    const initialViewState =
      initial.activeView || initial.view || viewParam || "analytics";
    const initialDatasetState =
      initial.selectedDataset !== undefined ? initial.selectedDataset : datasetParam;

    const [state, setState] = useState(initial);
    const [view, setView] = useState(initialViewState);
    const [dataset, setDataset] = useState(initialDatasetState);
    const [version, setVersion] = useState(
      initial.selectedVersion ||
        initial.boxVersions?.[0] ||
        initial.versions?.[0] ||
        ""
    );
    const [report, setReport] = useState(initial.reports?.initial || "");
    const [reportContent, setReportContent] = useState({
      headers: [],
      rows: [],
      loading: false,
      error: "",
    });
    const [compare, setCompare] = useState(() => {
      const defaults = initial.compare?.defaults || {};
      const first = initial.versions?.[0] || "";
      const second = initial.versions?.[1] || first;
      return {
        versionA: defaults.versionA || first,
        versionB: defaults.versionB || second,
        filter: defaults.filter || "all",
      };
    });
    const [loading, setLoading] = useState(false);
    const [loadError, setLoadError] = useState("");
    const [reloadToken, setReloadToken] = useState(0);
    const initialFetchRef = useRef(false);

    const endpoints = state.endpoints || initial.endpoints || {};
    const dashboardEndpoint = endpoints.dashboard || "/api/dashboard";
    const csvEndpoint = endpoints.csv || "/api/csv";
    const downloadEndpoint = endpoints.download || "/download";

    const datasetOptions = useMemo(() => {
      const opts = [...(state.datasetOptions || [])];
      if (!opts.includes("")) {
        opts.unshift("");
      }
      if (dataset && !opts.includes(dataset)) {
        opts.push(dataset);
      }
      return opts;
    }, [state.datasetOptions, dataset]);

    const updateUrl = useCallback((changes) => {
      const url = new URL(window.location.href);
      const apply = (key, value) => {
        if (value) {
          url.searchParams.set(key, value);
        } else {
          url.searchParams.delete(key);
        }
      };
      if ("dataset" in changes) apply("dataset", changes.dataset);
      if ("view" in changes) apply("view", changes.view);
      if ("version" in changes) apply("version", changes.version);
      if ("compareA" in changes) apply("compareA", changes.compareA);
      if ("compareB" in changes) apply("compareB", changes.compareB);
      if ("filter" in changes) apply("filter", changes.filter);
      if ("report" in changes) apply("report", changes.report);
      window.history.replaceState({}, "", url.toString());
    }, []);

    const loadState = useCallback(
      async (overrides = {}) => {
        const params = new URLSearchParams();
        const datasetValue =
          overrides.dataset !== undefined ? overrides.dataset : dataset;
        const viewValue = overrides.view || view;
        if (datasetValue) params.set("dataset", datasetValue);
        if (viewValue) params.set("view", viewValue);
        if (overrides.version) params.set("version", overrides.version);
        if (overrides.compareA) params.set("compareA", overrides.compareA);
        if (overrides.compareB) params.set("compareB", overrides.compareB);
        if (overrides.filter) params.set("filter", overrides.filter);

        setLoading(true);
        setLoadError("");
        try {
          const response = await fetch(
            `${dashboardEndpoint}?${params.toString()}`
          );
          if (!response.ok) {
            throw new Error(
              `Dashboard request failed (status ${response.status}).`
            );
          }
          const payload = await response.json();
          setState(payload);
          const defaults = payload.compare?.defaults || {};
          const first = payload.versions?.[0] || "";
          const second = payload.versions?.[1] || first;
          const chosenVersion =
            payload.selectedVersion ||
            payload.boxVersions?.[0] ||
            payload.versions?.[0] ||
            "";
          setDataset(payload.selectedDataset || "");
          setView(payload.activeView || viewValue);
          setVersion(chosenVersion);
          setCompare({
            versionA: defaults.versionA || first,
            versionB: defaults.versionB || second,
            filter: defaults.filter || "all",
          });
          setReport(payload.reports?.initial || "");
          setReportContent({ headers: [], rows: [], loading: false, error: "" });
          updateUrl({
            dataset: payload.selectedDataset || "",
            view: payload.activeView || viewValue,
            version: chosenVersion || null,
            compareA: defaults.versionA || null,
            compareB: defaults.versionB || null,
            filter:
              defaults.filter && defaults.filter !== "all"
                ? defaults.filter
                : null,
            report: payload.reports?.initial || null,
          });
        } catch (error) {
          setLoadError(error.message || "Unable to refresh dashboard data.");
        } finally {
          setLoading(false);
        }
      },
      [dashboardEndpoint, dataset, updateUrl, view]
    );

    useEffect(() => {
      if (initialFetchRef.current) {
        return;
      }
      initialFetchRef.current = true;
      if (Array.isArray(initial.versions) && initial.versions.length) {
        return;
      }
      const overrides = { view: initialViewState };
      if (initialDatasetState) {
        overrides.dataset = initialDatasetState;
      }
      loadState(overrides);
    }, [initial.versions, initialDatasetState, initialViewState, loadState]);

    const loadReport = useCallback(async () => {
      if (!report) {
        setReportContent({ headers: [], rows: [], loading: false, error: "" });
        return;
      }
      const params = new URLSearchParams({ file: report });
      if (dataset) params.set("dataset", dataset);
      setReportContent((prev) => ({ ...prev, loading: true, error: "" }));
      try {
        const response = await fetch(`${csvEndpoint}?${params.toString()}`);
        if (!response.ok) {
          throw new Error("Unable to load CSV content.");
        }
        const payload = await response.json();
        setReportContent({
          headers: payload.headers || [],
          rows: payload.rows || [],
          loading: false,
          error: "",
        });
      } catch (error) {
        setReportContent({
          headers: [],
          rows: [],
          loading: false,
          error: error.message || "Unable to load CSV content.",
        });
      }
    }, [csvEndpoint, dataset, report]);

    useEffect(() => {
      loadReport();
    }, [loadReport, reloadToken]);

    const compareRows = useMemo(() => {
      const services = state.compare?.services || [];
      const data = state.compare?.data || {};
      return services
        .map((service) => {
          const svcData = data[service] || {};
          const a = svcData[compare.versionA];
          const b = svcData[compare.versionB];
          if (
            (a === undefined || a === null) &&
            (b === undefined || b === null)
          ) {
            return null;
          }
          const diff =
            a !== undefined && a !== null && b !== undefined && b !== null
              ? b - a
              : null;
          const pct = diff !== null && a ? (diff / a) * 100 : null;
          let impact = "neutral";
          if (pct !== null) {
            if (pct <= -30) impact = "improve";
            else if (pct >= 30) impact = "regress";
          }
          if (compare.filter === "positive" && impact !== "improve") {
            return null;
          }
          if (compare.filter === "negative" && impact !== "regress") {
            return null;
          }
          return { service, a, b, diff, pct, impact };
        })
        .filter(Boolean);
    }, [state.compare, compare]);

    const analyticsView = html`<${AnalyticsPanel}
      state=${state}
      version=${version}
      onVersionChange=${(next) => {
        setVersion(next);
        updateUrl({ version: next || null });
      }}
    />`;

  const reportsPanel = html`<div className="flex h-[calc(100vh-6rem)] gap-6">
      <aside className="w-64 flex-shrink-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-gray-600">
          CSV Files
        </div>
        <div className="h-[calc(100%-3rem)] space-y-2 overflow-y-auto px-4 py-3">
          ${(state.reports?.files || []).map((file) => {
            const active = file === report;
            return html`<button
              key=${file}
              type="button"
              className=${classNames(
                "w-full rounded-md border px-3 py-2 text-left text-sm transition focus:outline-none focus:ring-2 focus:ring-indigo-300",
                active
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700 shadow-sm"
                  : "border-gray-200 bg-white text-gray-700 hover:border-indigo-300 hover:text-indigo-600"
              )}
              onClick=${() => {
                setReport(file);
                updateUrl({ report: file });
              }}
            >
              ${file}
            </button>`;
          })}
        </div>
      </aside>
      <section className="flex min-h-[420px] flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <header className="flex flex-col gap-3 border-b border-gray-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              ${report || "Select a CSV report"}
            </h2>
            ${dataset
              ? html`<p className="text-sm text-gray-500">Dataset: ${dataset}</p>`
              : null}
          </div>
          <div className="flex items-center gap-2">
            ${report
              ? html`<a
                  className="rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:border-indigo-400 hover:text-indigo-600"
                  href=${`${downloadEndpoint}?file=${encodeURIComponent(
                    report
                  )}${dataset ? `&dataset=${encodeURIComponent(dataset)}` : ""}`}
                >
                  Download CSV
                </a>`
              : null}
            ${report
              ? html`<button
                  type="button"
                  className="rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:border-indigo-400 hover:text-indigo-600"
                  onClick=${() => setReloadToken((n) => n + 1)}
                >
                  Refresh
                </button>`
              : null}
          </div>
        </header>
        <div className="flex-1 overflow-hidden">
          ${reportContent.loading
            ? html`<div className="flex h-full items-center justify-center text-sm text-gray-500">
                Loading CSV data...
              </div>`
            : null}
          ${!reportContent.loading && reportContent.error
            ? html`<div className="flex h-full items-center justify-center px-6 text-center text-sm text-rose-600">
                ${reportContent.error}
              </div>`
            : null}
          ${!reportContent.loading &&
          !reportContent.error &&
          reportContent.headers.length
            ? html`<div className="max-h-[70vh] overflow-auto">
                <table className="min-w-full divide-y divide-gray-200 text-xs sm:text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      ${reportContent.headers.map(
                        (header, idx) =>
                          html`<th
                            key=${`head-${idx}`}
                            className="px-4 py-2 text-left font-semibold uppercase tracking-wide text-gray-600"
                          >
                            ${header}
                          </th>`
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    ${reportContent.rows.map(
                      (row, rowIdx) =>
                        html`<tr key=${`row-${rowIdx}`}>
                          ${row.map(
                            (cell, cellIdx) =>
                              html`<td
                                key=${`cell-${rowIdx}-${cellIdx}`}
                                className="whitespace-nowrap px-4 py-2 text-gray-700"
                              >
                                ${cell}
                              </td>`
                          )}
                        </tr>`
                    )}
                  </tbody>
                </table>
              </div>`
            : null}
          ${!reportContent.loading &&
          !reportContent.error &&
          !reportContent.headers.length
            ? html`<div className="flex h-full items-center justify-center text-sm text-gray-500">
                No rows available in this CSV.
              </div>`
            : null}
        </div>
      </section>
    </div>`;

    const comparePanel = html`<div className="space-y-6">
      <section className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            Version Comparison
          </h2>
          <p className="text-sm text-gray-500">
            Highlight improvements or regressions between two versions.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          ${[
            { label: "Baseline", value: compare.versionA, key: "versionA" },
            { label: "Target", value: compare.versionB, key: "versionB" },
          ].map(
            (item) =>
              html`<label key=${`cmp-${item.key}`} className="flex items-center gap-2 text-sm">
                <span className="text-gray-600">${item.label}</span>
                <select
                  className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                  value=${item.value}
                  onChange=${(event) => {
                    const next = { ...compare, [item.key]: event.target.value };
                    setCompare(next);
                    updateUrl({
                      compareA: next.versionA || null,
                      compareB: next.versionB || null,
                      filter:
                        next.filter && next.filter !== "all"
                          ? next.filter
                          : null,
                    });
                  }}
                >
                  ${(state.versions || []).map(
                    (version) =>
                      html`<option key=${`cmp-opt-${version}`} value=${version}>
                        ${version}
                      </option>`
                  )}
                </select>
              </label>`
          )}
          <label className="flex items-center gap-2 text-sm">
            <span className="text-gray-600">Filter</span>
            <select
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              value=${compare.filter}
              onChange=${(event) => {
                const next = { ...compare, filter: event.target.value };
                setCompare(next);
                updateUrl({
                  compareA: next.versionA || null,
                  compareB: next.versionB || null,
                  filter:
                    next.filter && next.filter !== "all"
                      ? next.filter
                      : null,
                });
              }}
            >
              <option value="all">All services</option>
              <option value="positive">≥30% faster</option>
              <option value="negative">≥30% slower</option>
            </select>
          </label>
        </div>
      </section>
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="max-h-[70vh] overflow-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                  Service
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                  ${compare.versionA || "Baseline"}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                  ${compare.versionB || "Target"}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                  Δ (ms)
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                  Δ (%)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              ${compareRows.length
                ? compareRows.map((row) => {
                    const tone =
                      row.impact === "regress"
                        ? "text-rose-600"
                        : row.impact === "improve"
                        ? "text-emerald-600"
                        : "text-gray-700";
                    const badge =
                      row.impact === "improve"
                        ? html`<span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                            Improved
                          </span>`
                        : row.impact === "regress"
                        ? html`<span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                            Regressed
                          </span>`
                        : null;
                    return html`<tr key=${row.service}>
                      <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-800">
                        <span className="flex items-center gap-2">
                          ${row.service}
                          ${badge}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                        ${formatMs(row.a)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                        ${formatMs(row.b)}
                      </td>
                      <td className=${classNames(
                        "whitespace-nowrap px-4 py-3 font-medium",
                        tone
                      )}>
                        ${row.diff !== null
                          ? `${row.diff > 0 ? "+" : ""}${formatMs(row.diff)}`
                          : MISSING_VALUE}
                      </td>
                      <td className=${classNames(
                        "whitespace-nowrap px-4 py-3 font-medium",
                        tone
                      )}>
                        ${row.pct !== null
                          ? `${row.pct > 0 ? "+" : ""}${formatPct(row.pct)}`
                          : MISSING_VALUE}
                      </td>
                    </tr>`;
                  })
                : html`<tr>
                    <td
                      colspan="5"
                      className="px-4 py-6 text-center text-sm text-gray-500"
                    >
                      No services match the selected filter.
                    </td>
                  </tr>`}
            </tbody>
          </table>
        </div>
      </section>
    </div>`;

  return html`<div className="flex h-screen bg-gray-100 overflow-hidden">
      <aside className="flex h-full w-20 flex-shrink-0 flex-col items-center gap-4 bg-gray-900 py-6 text-gray-200 shadow-lg">
        ${VIEWS.map((item) => {
          const active = item.id === view;
          return html`<button
            key=${item.id}
            type="button"
            className=${classNames(
              "flex w-16 flex-col items-center gap-1 rounded-lg px-2 py-3 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-300",
              active
                ? "bg-indigo-500 text-white shadow-md"
                : "hover:bg-gray-800 hover:text-white"
            )}
            onClick=${() => {
              setView(item.id);
              updateUrl({ view: item.id });
            }}
          >
            <span className="text-xl">${item.icon}</span>
            <span>${item.label}</span>
          </button>`;
        })}
      </aside>
      <div className="flex h-full flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-30 flex-shrink-0 border-b border-gray-200 bg-white bg-opacity-95 backdrop-blur">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-6 py-4">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                Service Performance Metric
              </h1>
              <p className="text-sm text-gray-500">
                View: ${VIEWS.find((item) => item.id === view)?.label || "Analytics"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-600" for="datasetSelect">
                Dataset
              </label>
              <select
                id="datasetSelect"
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                value=${dataset}
                onChange=${(event) => {
                  const value = event.target.value;
                  setDataset(value);
                  setReport("");
                  updateUrl({ dataset: value, report: null });
                  loadState({ dataset: value });
                }}
              >
                ${datasetOptions.map(
                  (option) =>
                    html`<option key=${`dataset-${option || "default"}`} value=${option}>
                      ${option || "Default"}
                    </option>`
                )}
              </select>
              ${loading
                ? html`<span className="text-xs text-gray-500">Loading...</span>`
                : null}
            </div>
          </div>
        </header>
        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col overflow-y-auto px-6 py-6">
          ${loadError
            ? html`<div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                ${loadError}
              </div>`
            : null}
          ${view === "analytics" ? analyticsView : null}
          ${view === "reports" ? reportsPanel : null}
          ${view === "compare" ? comparePanel : null}
        </main>
      </div>
    </div>`;
  };

  const root = document.getElementById("root");
  if (!root) {
    console.error("Root element not found.");
    return;
  }
  const initialState = window.__INITIAL_STATE__ || {};
  ReactDOM.createRoot(root).render(html`<${App} initial=${initialState} />`);
})();
