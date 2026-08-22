/**
 * D3.js Force-Directed Provenance DAG Visualizer
 * Renders independent root sources vs pruned echo-chamber scraper nodes.
 */

class DAGVisualizer {
  constructor(containerId) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.svg = null;
    this.simulation = null;
  }

  render(dagData) {
    if (!this.container) return;
    this.container.innerHTML = "";

    const width = this.container.clientWidth || 450;
    const height = this.container.clientHeight || 320;

    const svg = d3.select(`#${this.containerId}`)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Define Arrow Marker for Directed Citation Edges
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 22)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", "#64748b")
      .attr("d", "M0,-5L10,0L0,5");

    const nodes = dagData.nodes.map(d => ({ ...d }));
    const links = dagData.edges.map(d => ({ ...d }));

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(35));

    // Draw Links
    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", d => d.relation === "SYNDICATED_COPY" ? "#ef4444" : "#4facfe")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", d => d.relation === "SYNDICATED_COPY" ? "4,4" : "none")
      .attr("marker-end", "url(#arrow)");

    // Draw Nodes
    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Node Circles
    node.append("circle")
      .attr("r", d => d.is_root ? 16 : 12)
      .attr("fill", d => d.is_root ? "#10b981" : "#ef4444")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 2)
      .attr("opacity", d => d.is_root ? 1.0 : 0.6)
      .attr("class", d => d.is_root ? "pulsing-glow" : "");

    // Node Labels
    node.append("text")
      .text(d => d.domain.length > 15 ? d.domain.substring(0, 13) + "..." : d.domain)
      .attr("x", 0)
      .attr("y", 26)
      .attr("text-anchor", "middle")
      .attr("fill", "#cbd5e1")
      .attr("font-size", "10px")
      .attr("font-weight", "500");

    // Tooltip Hover
    node.append("title")
      .text(d => `Domain: ${d.domain}\nRoot Source: ${d.is_root ? "YES (Valid Evidence)" : "NO (Pruned Scraper)"}\nAuthority: ${d.authoritativeness * 100}%`);

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });
  }
}
