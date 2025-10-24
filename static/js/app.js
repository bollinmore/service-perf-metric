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
    { id: "api", label: "API", icon: "\u{1F4D6}" },
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
    const [importingDataset, setImportingDataset] = useState(false);
    const [importFeedback, setImportFeedback] = useState({ error: "", success: "" });
    const folderInputRef = useRef(null);
    const zipInputRef = useRef(null);
    const [showImportMenu, setShowImportMenu] = useState(false);
    const [collapsedGroups, setCollapsedGroups] = useState({});
    const initialFetchRef = useRef(false);

    const endpoints = state.endpoints || initial.endpoints || {};
    const dashboardEndpoint = endpoints.dashboard || "/api/dashboard";
    const csvEndpoint = endpoints.csv || "/api/csv";
    const downloadEndpoint = endpoints.download || "/download";
    const importEndpoint = endpoints.importDataset || "/api/datasets/import";
    const deleteEndpoint = endpoints.deleteDataset || "/api/datasets/delete";

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

    const handleDatasetImport = useCallback(
      async (event) => {
        const input = event.target;
        const files = input?.files;
        if (!files || !files.length || importingDataset) {
          if (input) {
            input.value = "";
          }
          return;
        }

        setImportingDataset(true);
        setImportFeedback({ error: "", success: "" });

        try {
          const fileArray = Array.from(files);
          const relativePaths = fileArray.map((file) => file.webkitRelativePath || file.name);
          const topLevels = Array.from(
            new Set(
              relativePaths
                .map((path) => (path || "").split(/[\\/]/)[0])
                .filter(Boolean)
            )
          );

          let datasetName = topLevels.length === 1 ? topLevels[0] : "";
          if (!datasetName) {
            const proposed = `dataset-${new Date().toISOString().replace(/[:.]/g, "-")}`;
            datasetName = window.prompt("Enter a name for this dataset", proposed) || "";
          } else if (topLevels.length > 1) {
            const proposed = `dataset-${new Date().toISOString().split("T")[0]}`;
            const userInput = window.prompt(
              "Multiple top-level folders detected. Enter a dataset name to use",
              datasetName || proposed
            );
            datasetName = (userInput || datasetName || proposed).trim();
          }

          if (!datasetName) {
            setImportingDataset(false);
            setImportFeedback({ error: "Dataset import cancelled (missing name).", success: "" });
            if (input) {
              input.value = "";
            }
            return;
          }

          const formData = new FormData();
          formData.append("datasetName", datasetName);
          fileArray.forEach((file) => {
            const relative = file.webkitRelativePath || file.name;
            formData.append("folder", file, relative);
          });

          const response = await fetch(importEndpoint, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            let message = `Failed to import dataset (status ${response.status}).`;
            try {
              const data = await response.clone().json();
              if (data && typeof data === "object") {
                message = data.message || data.error || message;
              }
            } catch (jsonError) {
              try {
                const text = await response.text();
                if (text) {
                  const trimmed = text.trim();
                  message = trimmed.startsWith("<") ? message : trimmed;
                }
              } catch (textError) {
                console.warn("Failed to read import error payload", textError);
              }
            }
            if (response.status === 409) {
              const guidance = `Dataset '${datasetName}' already exists. Rename the new dataset or remove the existing folder under 'data/${datasetName}' before importing again.`;
              message = `${message} ${guidance}`.trim();
            } else if (response.status === 400) {
              const guidance =
                "Import expects either a dataset folder (use the folder picker) or a ZIP that contains the dataset root with at least three version folders, each holding a PerformanceLog directory. Please pick a valid dataset and try again.";
              message = `${message} ${guidance}`.trim();
            }
            throw new Error(message);
          }

          const payload = await response.json();
          const importedName = payload?.dataset || datasetName;
          const overrides = { view: "reports" };
          if (importedName) {
            overrides.dataset = importedName;
          }
          await loadState(overrides);
          setImportFeedback({
            error: "",
            success: payload?.message || "Dataset imported successfully.",
          });
        } catch (error) {
          setImportFeedback({
            success: "",
            error:
              error instanceof Error && error.message
                ? error.message
                : "Failed to import dataset.",
          });
        } finally {
          setImportingDataset(false);
          if (input) {
            input.value = "";
          }
        }
      },
      [importEndpoint, loadState, importingDataset]
    );

    const handleZipImport = useCallback(
      async (event) => {
        const input = event.target;
        const file = input?.files?.[0];
        if (!file || importingDataset) {
          if (input) input.value = "";
          return;
        }

        // Ask for datasetName (fallback to zip name without extension)
        const defaultName = (file.name || "").replace(/\.zip$/i, "");
        const name = window.prompt("Enter a dataset name", defaultName) || defaultName;
        if (!name) {
          if (input) input.value = "";
          return;
        }

        setImportingDataset(true);
        setImportFeedback({ error: "", success: "" });
        setShowImportMenu(false);

        try {
          const formData = new FormData();
          formData.append("file", file);
          formData.append("datasetName", name);
          const response = await fetch(importEndpoint, { method: "POST", body: formData });
          if (!response.ok) {
            let message = `Failed to import dataset (status ${response.status}).`;
            try {
              const data = await response.clone().json();
              if (data && typeof data === "object") {
                message = data.message || data.error || message;
              }
            } catch (jsonError) {
              try {
                const text = await response.text();
                if (text) {
                  const trimmed = text.trim();
                  message = trimmed.startsWith("<") ? message : trimmed;
                }
              } catch {}
            }
            if (response.status === 409) {
              const guidance = `Dataset '${name}' already exists. Rename the new dataset or remove the existing folder under 'data/${name}' before importing again.`;
              message = `${message} ${guidance}`.trim();
            } else if (response.status === 400) {
              const guidance =
                "Import expects either a dataset folder (use the folder picker) or a ZIP that contains the dataset root with at least three version folders, each holding a PerformanceLog directory. Please pick a valid dataset and try again.";
              message = `${message} ${guidance}`.trim();
            }
            throw new Error(message);
          }

          const payload = await response.json();
          const importedName = payload?.dataset || name;
          const overrides = { view: "reports", dataset: importedName };
          await loadState(overrides);
          setImportFeedback({ error: "", success: payload?.message || "Dataset imported successfully." });
        } catch (error) {
          setImportFeedback({
            success: "",
            error: error instanceof Error && error.message ? error.message : "Failed to import dataset.",
          });
        } finally {
          setImportingDataset(false);
          if (input) input.value = "";
        }
      },
      [importEndpoint, loadState, importingDataset]
    );

    useEffect(() => {
      if (view !== "reports" && (importFeedback.error || importFeedback.success)) {
        setImportFeedback({ error: "", success: "" });
      }
    }, [importFeedback.error, importFeedback.success, view]);

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
          if (compare.filter === "faster" && !(diff !== null && diff < 0)) {
            return null;
          }
          if (compare.filter === "slower" && !(diff !== null && diff > 0)) {
            return null;
          }
          return { service, a, b, diff, pct, impact };
        })
        .filter(Boolean);
    }, [state.compare, compare]);

    const apiDocsHtml = state.apiDocsHtml || initial.apiDocsHtml || "";
    const apiDocsView = html`<section
      className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 text-sm leading-relaxed shadow-sm"
      dangerouslySetInnerHTML=${{
        __html:
          apiDocsHtml && apiDocsHtml.trim()
            ? apiDocsHtml
            : "<p>Backend API documentation is not available.</p>",
      }}
    ></section>`;

    const reportGroups = useMemo(() => {
      const groups = state.reports?.groups;
      if (groups && Object.keys(groups).length) {
        return Object.entries(groups);
      }
      const files = state.reports?.files || [];
      if (!files.length) {
        return [];
      }
      const label = state.selectedDataset || "Current Dataset";
      return [[label, files]];
    }, [state.reports, state.selectedDataset]);

    useEffect(() => {
      setCollapsedGroups((prev) => {
        const next = {};
        reportGroups.forEach(([name]) => {
          next[name] = Object.prototype.hasOwnProperty.call(prev, name)
            ? prev[name]
            : false;
        });
        return next;
      });
    }, [reportGroups]);

    const analyticsView = html`<${AnalyticsPanel}
      state=${state}
      version=${version}
      onVersionChange=${(next) => {
        setVersion(next);
        updateUrl({ version: next || null });
      }}
    />`;

  const reportsPanel = html`<div className="flex h-[calc(100vh-6rem)] gap-6 overflow-visible">
      <aside className="flex w-64 flex-shrink-0 flex-col overflow-visible rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-2 border-b border-gray-200 px-4 py-3">
          <span className="text-sm font-semibold uppercase tracking-wide text-gray-600">
            CSV Files
          </span>
          <div className="relative">
            <input
              ref=${folderInputRef}
              type="file"
              multiple
              webkitdirectory=""
              mozdirectory=""
              directory=""
              className="hidden"
              onChange=${handleDatasetImport}
            />
            <input
              ref=${zipInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange=${handleZipImport}
            />
            <button
              type="button"
              className=${classNames(
                "rounded-full border border-gray-200 bg-white p-2 text-gray-600 shadow-sm transition hover:border-indigo-400 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300",
                importingDataset ? "cursor-not-allowed opacity-60" : ""
              )}
              title=${importingDataset ? "Importing dataset..." : "Import Dataset"}
              aria-label="Import Dataset"
              disabled=${importingDataset}
              onClick=${() => setShowImportMenu((v) => !v)}
            >
              <span className="sr-only">Import Dataset</span>
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 4v12" />
                <path d="M8 8l4-4 4 4" />
                <path d="M5 20h14" />
              </svg>
            </button>
            ${showImportMenu
              ? html`<div className="absolute right-0 z-10 mt-2 w-44 rounded-md border border-gray-200 bg-white p-1 text-sm shadow-lg">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-gray-50"
                    onClick=${() => {
                      setShowImportMenu(false);
                      folderInputRef.current?.click();
                    }}
                  >
                    <span>Import Folder…</span>
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-gray-50"
                    onClick=${() => {
                      setShowImportMenu(false);
                      zipInputRef.current?.click();
                    }}
                  >
                    <span>Import ZIP…</span>
                  </button>
                </div>`
              : null}
          </div>
        </div>
        ${importFeedback.error || importFeedback.success
          ? html`<div
              className=${classNames(
                "px-4 py-2 text-xs",
                importFeedback.error
                  ? "bg-rose-50 text-rose-700"
                  : "bg-emerald-50 text-emerald-700"
              )}
            >
              ${importFeedback.error || importFeedback.success}
            </div>`
          : null}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          ${reportGroups.length
            ? reportGroups.map(([groupName, files]) =>
                html`<div key=${`group-${groupName}`} className="space-y-2">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-md px-2 py-1 text-xs font-semibold uppercase tracking-wide text-gray-500 transition hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  title="Expand/Collapse"
                  onClick=${() =>
                    setCollapsedGroups((prev) => ({
                      ...prev,
                      [groupName]: !prev[groupName],
                    }))}
                >
                  <span>${groupName}</span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600">
                    ${files.length}
                  </span>
                  <svg
                    className=${classNames(
                      "h-3 w-3 transition-transform",
                      collapsedGroups[groupName] ? "-rotate-90" : "rotate-0"
                    )}
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M6 8l4 4 4-4" />
                  </svg>
                </button>
                <button
                  type="button"
                  className="rounded-full border border-gray-200 bg-white p-1 text-gray-500 shadow-sm transition hover:border-rose-300 hover:text-rose-600 focus:outline-none focus:ring-2 focus:ring-rose-300"
                  title="Delete Dataset"
                  aria-label="Delete Dataset"
                  onClick=${async () => {
                    const datasetName = state.selectedDataset || groupName;
                    if (!datasetName) return;
                    const ok = window.confirm(`Move dataset '${datasetName}' to recycle folder?`);
                    if (!ok) return;
                    try {
                      const form = new FormData();
                      form.append("dataset", datasetName);
                      const resp = await fetch(deleteEndpoint, { method: "POST", body: form });
                      if (!resp.ok) {
                        let msg = `Failed to delete dataset (status ${resp.status}).`;
                        try {
                          const data = await resp.clone().json();
                          msg = data?.message || data?.error || msg;
                        } catch {}
                        if (resp.status === 404) {
                          msg = `${msg} It may have already been removed. Try refreshing, switch to another dataset, or check the 'data/' and 'result/' folders.`;
                        }
                        alert(msg);
                        return;
                      }
                      // Optimistic UI update so the left list reflects removal immediately
                      setState((prev) => ({
                        ...prev,
                        datasetOptions: (prev.datasetOptions || []).filter((d) => d !== datasetName),
                        selectedDataset: prev.selectedDataset === datasetName ? "" : prev.selectedDataset,
                        reports: prev.selectedDataset === datasetName
                          ? { files: [], groups: {}, initial: "" }
                          : prev.reports,
                      }));
                      // Then reload from server to re-sync
                      await loadState({ view: "reports", dataset: state.selectedDataset === datasetName ? "" : state.selectedDataset });
                      setImportFeedback({ error: "", success: `Dataset '${datasetName}' moved to recycle.` });
                    } catch (e) {
                      alert(e?.message || "Failed to delete dataset.");
                    }
                  }}
                >
                  <svg
                    className="h-3.5 w-3.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18" />
                    <path d="M8 6V4h8v2" />
                    <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14" />
                    <path d="M10 11v6M14 11v6" />
                  </svg>
                </button>
              </div>
              ${collapsedGroups[groupName]
                ? null
                : html`<div className="space-y-2">
                    ${files.map((file) => {
                      const active = file === report;
                      return html`<button
                        key=${`${groupName}-${file}`}
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
                  </div>`}
            </div>`
              )
            : html`<div className="text-sm text-gray-500">No CSV files available.</div>`}
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
        <div className="flex-1 overflow-auto">
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
            ? html`<div className="min-h-full">
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
              <option value="faster">Faster</option>
              <option value="slower">Slower</option>
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
                      row.diff === null || row.diff === 0
                        ? "text-gray-700"
                        : row.diff > 0
                        ? "text-red-600"
                        : "text-green-600";
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
          ${view === "api" ? apiDocsView : null}
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
