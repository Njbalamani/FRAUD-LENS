(function () {
  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  ready(function () {
    var reveals = document.querySelectorAll(".reveal");
    if (window.gsap) {
      gsap.fromTo(reveals, { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.65, stagger: 0.08, ease: "power2.out" });
    } else {
      reveals.forEach(function (element) { element.style.opacity = 1; });
    }

    var dataElement = document.getElementById("risk-distribution-data");
    var canvas = document.getElementById("riskChart");
    if (dataElement && canvas && window.Chart) {
      var values = JSON.parse(dataElement.textContent || "[]");
      var labels = values.length ? values.map(function (item) { return item.risk_level; }) : ["low", "medium", "high", "critical"];
      var counts = values.length ? values.map(function (item) { return item.count; }) : [0, 0, 0, 0];
      new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: ["rgba(74,222,128,0.78)", "rgba(212,175,55,0.78)", "rgba(245,165,36,0.82)", "rgba(255,95,109,0.82)"],
            borderColor: "rgba(255,255,255,0.08)",
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { labels: { color: "#91a0b5" } },
            tooltip: { callbacks: { label: function (context) { return context.label + ": " + context.parsed; } } }
          }
        }
      });
    }

    var trendElement = document.getElementById("risk-trend-data");
    var trendCanvas = document.getElementById("trendChart");
    if (trendElement && trendCanvas && window.Chart) {
      var trend = JSON.parse(trendElement.textContent || "[]");
      new Chart(trendCanvas, {
        type: "line",
        data: {
          labels: trend.map(function (item) { return item.day; }),
          datasets: [
            {
              label: "Scores",
              data: trend.map(function (item) { return item.count; }),
              borderColor: "rgba(212,175,55,0.95)",
              backgroundColor: "rgba(212,175,55,0.14)",
              fill: true,
              tension: 0.35
            },
            {
              label: "Average risk",
              data: trend.map(function (item) { return Math.round((item.average || 0) * 10) / 10; }),
              borderColor: "rgba(184,196,212,0.85)",
              backgroundColor: "rgba(184,196,212,0.08)",
              fill: false,
              tension: 0.35
            }
          ]
        },
        options: {
          responsive: true,
          scales: {
            x: { ticks: { color: "#91a0b5" }, grid: { color: "rgba(255,255,255,0.04)" } },
            y: { beginAtZero: true, ticks: { color: "#91a0b5" }, grid: { color: "rgba(255,255,255,0.04)" } }
          },
          plugins: { legend: { labels: { color: "#91a0b5" } } }
        }
      });
    }

    function cookieValue(name) {
      var parts = document.cookie.split(";");
      for (var index = 0; index < parts.length; index += 1) {
        var part = parts[index].trim();
        if (part.indexOf(name + "=") === 0) {
          return decodeURIComponent(part.substring(name.length + 1));
        }
      }
      return "";
    }

    function apiError(response, fallback) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        throw new Error(data.detail || fallback + " (status " + response.status + ")");
      });
    }

    var caseButton = document.getElementById("create-case-from-findings");
    var caseStatus = document.getElementById("case-create-status");
    var caseData = document.getElementById("case-finding-ids");
    if (caseButton && caseStatus && caseData) {
      var findingIds = JSON.parse(caseData.textContent || "[]");
      if (!findingIds.length) {
        caseButton.disabled = true;
        caseStatus.textContent = "No high-severity findings are available for triage.";
      }
      caseButton.addEventListener("click", function () {
        caseButton.disabled = true;
        caseStatus.textContent = "Creating a case from " + findingIds.length + " findings…";
        fetch("/api/investigations/cases/from-findings/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": cookieValue("csrftoken")
          },
          body: JSON.stringify({
            finding_ids: findingIds,
            title: "High-risk signal review",
            priority: "high"
          })
        })
          .then(function (response) {
            if (!response.ok) {
              return apiError(response, "Unable to create case");
            }
            return response.json();
          })
          .then(function (data) {
            caseStatus.textContent = "Created " + data.case_id + " with " + (data.finding_count || findingIds.length) + " findings.";
            setTimeout(function () { window.location.reload(); }, 900);
          })
          .catch(function (error) {
            caseStatus.textContent = error.message;
            caseButton.disabled = false;
          });
      });
    }

    var uploadButton = document.getElementById("upload-csv");
    var uploadInput = document.getElementById("csv-file");
    var uploadStatus = document.getElementById("upload-status");
    if (uploadButton && uploadInput && uploadStatus) {
      uploadButton.addEventListener("click", function () {
        var file = uploadInput.files[0];
        if (!file) {
          uploadStatus.textContent = "Choose a CSV file first.";
          return;
        }
        var maxMb = parseFloat(uploadButton.getAttribute("data-max-mb") || "5");
        if (file.size > maxMb * 1024 * 1024) {
          uploadStatus.textContent = "File exceeds the " + maxMb + " MB limit.";
          return;
        }
        var payload = new FormData();
        payload.append("file", file);
        uploadButton.disabled = true;
        uploadStatus.textContent = "Validating " + file.name + "…";
        fetch("/api/transactions/import/", {
          method: "POST",
          headers: { "X-CSRFToken": cookieValue("csrftoken") },
          body: payload
        })
          .then(function (response) {
            if (!response.ok) {
              return apiError(response, "Unable to import CSV");
            }
            return response.json();
          })
          .then(function (data) {
            uploadStatus.textContent = "Imported " + data.rows_imported + " rows; rejected " + data.rows_rejected + "; duplicates " + data.duplicate_count + ".";
            setTimeout(function () { window.location.reload(); }, 900);
          })
          .catch(function (error) {
            uploadStatus.textContent = error.message;
            uploadButton.disabled = false;
          });
      });
    }

    var runButton = document.getElementById("run-detection");
    var runStatus = document.getElementById("run-status");
    if (runButton && runStatus) {
      runButton.addEventListener("click", function () {
        runButton.disabled = true;
        runButton.textContent = "Running…";
        runStatus.textContent = "Recalculating rules, anomaly signals, and risk scores.";
        fetch("/api/detection/analyze/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": cookieValue("csrftoken")
          },
          body: JSON.stringify({ force: true })
        })
          .then(function (response) {
            if (!response.ok) {
              throw new Error("Request failed with status " + response.status);
            }
            return response.json();
          })
          .then(function (data) {
            runStatus.textContent = "Complete: " + data.transactions_analyzed + " transactions, " + data.high_risk_count + " high-risk findings.";
            setTimeout(function () { window.location.reload(); }, 900);
          })
          .catch(function (error) {
            runStatus.textContent = "Unable to run detection. " + error.message;
          })
          .finally(function () {
            runButton.disabled = false;
            runButton.textContent = "Run detection";
          });
      });
    }

    var reportForm = document.getElementById("report-generate-form");
    var reportStatus = document.getElementById("report-status");
    if (reportForm && reportStatus) {
      reportForm.addEventListener("submit", function (event) {
        event.preventDefault();
        var submitButton = reportForm.querySelector("button[type='submit']");
        var payload = {
          title: document.getElementById("report-title").value.trim() || undefined,
          kind: document.getElementById("report-kind").value,
          file_format: document.getElementById("report-format").value,
          days: parseInt(document.getElementById("report-days").value, 10) || 30
        };
        submitButton.disabled = true;
        reportStatus.textContent = "Generating " + payload.file_format.toUpperCase() + " report…";
        fetch("/api/reports/generate/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": cookieValue("csrftoken")
          },
          body: JSON.stringify(payload)
        })
          .then(function (response) {
            if (!response.ok) {
              return apiError(response, "Unable to generate report");
            }
            return response.json();
          })
          .then(function (data) {
            reportStatus.textContent = "Created " + data.file_name + ".";
            setTimeout(function () { window.location.reload(); }, 900);
          })
          .catch(function (error) {
            reportStatus.textContent = error.message;
            submitButton.disabled = false;
          });
      });
    }

    var filterInput = document.getElementById("table-filter");
    var table = document.getElementById("transaction-table");
    if (filterInput && table) {
      filterInput.addEventListener("input", function () {
        var term = filterInput.value.toLowerCase();
        table.querySelectorAll("tbody tr").forEach(function (row) {
          var text = row.textContent.toLowerCase();
          row.style.display = text.indexOf(term) >= 0 ? "" : "none";
        });
      });
    }
  });
})();
