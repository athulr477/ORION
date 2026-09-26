"""UML Activity Diagram Generator matching user's exact textbook reference diagram.
Features:
- Pure white background
- Exact sampled soft blue rounded rectangle action capsules (#97cef1) with crisp black borders
- Centered vertical flow with dual branch split-rejoin and right-side bypass to final node
- Folded-corner document note with dashed connector
- Textbook UML decision diamonds with guard conditions in brackets
- Solid black start circle and bullseye final node
- Continuous miter-joined polylines for crisp 90-degree corners with open V-arrowheads
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import os

def create_reference_activity_diagram():
    # Figure size: 9 x 13.5 inches, high-res 300 DPI
    fig, ax = plt.subplots(figsize=(9, 13.5), dpi=300)
    
    # Coordinate system: X: 0 to 100, Y: 0 to 135
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 135)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Exact sampled soft blue hex color from user's reference diagram (RGB: 151, 206, 241)
    C_BLUE = "#97cef1"
    C_BLACK = "#000000"
    C_WHITE = "#ffffff"
    
    # Helper drawing primitives
    def draw_action(x, y, w, h, text):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h, 
                             boxstyle="round,pad=0.2,rounding_size=1.2",
                             facecolor=C_BLUE, edgecolor=C_BLACK, linewidth=1.5, zorder=3)
        ax.add_patch(box)
        ax.text(x, y, text, fontsize=10.0, fontweight='normal', color=C_BLACK,
                ha='center', va='center', family='sans-serif', zorder=4)

    def draw_decision(x, y, w=3.8, h=3.4):
        diamond = Polygon([(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)],
                          closed=True, facecolor=C_BLUE, edgecolor=C_BLACK, linewidth=1.5, zorder=3)
        ax.add_patch(diamond)

    def draw_note(x, y, w, h, text):
        fold = 2.4
        verts = [
            (x - w/2, y - h/2),
            (x - w/2, y + h/2),
            (x + w/2 - fold, y + h/2),
            (x + w/2, y + h/2 - fold),
            (x + w/2, y - h/2),
            (x - w/2, y - h/2)
        ]
        poly = Polygon(verts, closed=True, facecolor=C_BLUE, edgecolor=C_BLACK, linewidth=1.4, zorder=3)
        ax.add_patch(poly)
        
        # Folded flap
        flap_verts = [
            (x + w/2 - fold, y + h/2),
            (x + w/2 - fold, y + h/2 - fold),
            (x + w/2, y + h/2 - fold)
        ]
        flap = Polygon(flap_verts, closed=True, facecolor=C_BLUE, edgecolor=C_BLACK, linewidth=1.2, zorder=4)
        ax.add_patch(flap)
        
        ax.text(x - 0.4, y, text, fontsize=8.6, color=C_BLACK, ha='center', va='center', family='sans-serif', zorder=5)

    def draw_start_node(x, y, r=1.5):
        start = Circle((x, y), r, facecolor=C_BLACK, edgecolor=C_BLACK, linewidth=1.5, zorder=3)
        ax.add_patch(start)

    def draw_end_node(x, y, r_outer=1.7, r_inner=1.05):
        outer = Circle((x, y), r_outer, facecolor=C_WHITE, edgecolor=C_BLACK, linewidth=1.5, zorder=3)
        inner = Circle((x, y), r_inner, facecolor=C_BLACK, edgecolor=C_BLACK, linewidth=1.0, zorder=4)
        ax.add_patch(outer)
        ax.add_patch(inner)

    def draw_path_arrow(pts, color=C_BLACK, lw=1.3):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # Continuous line with miter join ensures corners have zero gaps or stubs
        ax.plot(xs, ys, color=color, lw=lw, solid_joinstyle='miter', zorder=2)
        # Open V-arrowhead at the terminus
        ax.annotate('', xy=pts[-1], xytext=pts[-2],
                    arrowprops=dict(arrowstyle="->", color=color, lw=lw,
                                    mutation_scale=14, shrinkA=0, shrinkB=0),
                    zorder=2)

    def draw_dashed_line(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color=C_BLACK, lw=1.3, linestyle=(0, (4, 4)), zorder=2)

    # =============================================================
    # Diagram Elements Placement (Uniform, Balanced Spacing)
    # =============================================================
    
    # 1. Start Node
    draw_start_node(50, 128)
    draw_path_arrow([(50, 126.5), (50, 120.3)])

    # 2. Action 1: Call Client and Set-up Appointment -> Receive PR & Ingest Requirements
    draw_action(50, 116.5, 33, 7.2, "Receive Pull Request and\nIngest Requirements")
    draw_path_arrow([(50, 112.9), (50, 106.7)])

    # 3. Decision 1: Diamond (center: 50, 105, w=3.8, h=3.4)
    draw_decision(50, 105, w=3.8, h=3.4)
    
    # Left branch: [semantic vector analysis]
    draw_path_arrow([(48.1, 105), (25, 105), (25, 97.6)])
    ax.text(36.5, 106.3, "[semantic vector analysis]", fontsize=8.8, ha='center', va='bottom', family='sans-serif')
    draw_action(25, 94, 25, 6.8, "Generate FastEmbed\nVector Embeddings")

    # Right branch: [structural assertion analysis]
    draw_path_arrow([(51.9, 105), (75, 105), (75, 97.6)])
    ax.text(63.5, 106.3, "[structural assertion analysis]", fontsize=8.8, ha='center', va='bottom', family='sans-serif')
    draw_action(75, 94, 25, 6.8, "Extract AST Assertions\n& Normalize Units")

    # Both branches rejoin into Action 3: Meet with the Client -> Execute Hungarian Matcher
    draw_path_arrow([(25, 90.6), (25, 81.5), (34.0, 81.5)])
    draw_path_arrow([(75, 90.6), (75, 81.5), (66.0, 81.5)])
    draw_action(50, 81.5, 31, 6.8, "Execute Kuhn-Munkres\nBipartite Matcher")

    # 4. Action 4: Send Follow-up Letter -> Compute Hybrid Risk Score
    draw_path_arrow([(50, 78.1), (50, 72.1)])
    draw_action(50, 68.5, 30, 6.8, "Compute Hybrid Risk Score\n& Classify Status")

    # 5. Decision 2: Diamond (center: 50, 57, w=3.8, h=3.4)
    draw_path_arrow([(50, 65.1), (50, 58.7)])
    draw_decision(50, 57, w=3.8, h=3.4)

    # Branch straight down: [specification drift detected] -> Create Proposal
    draw_path_arrow([(50, 55.3), (50, 48.6)])
    ax.text(48.8, 52.0, "[specification drift detected]", fontsize=8.8, ha='right', va='center', family='sans-serif')
    draw_action(50, 45, 32, 6.8, "Generate XAI Drift Summary\nvia Ollama LLM")

    # Folded document note on the left connected to Action 5
    draw_dashed_line(29.0, 45, 34.0, 45)
    draw_note(18.0, 45, 22.0, 9.0, "See the Activity Diagram\nfor Evidence-Grounded\nVerbalizer details")

    # Action 6: Send Proposal to Client -> Post Failure Check Run & Alert Jira
    draw_path_arrow([(50, 41.6), (50, 34.6)])
    draw_action(50, 31, 31, 6.8, "Post Check Run Failure\n& Alert Jira Issue")

    # Action 6 straight down into Final Node top
    # Final node is at y=12, r_outer=1.7, so top edge is at y=13.7
    draw_path_arrow([(50, 27.6), (50, 13.7)])

    # Branch right from Decision 2: [traceability verified / compliant] -> Bypass straight to Final Node right edge
    # Final node right edge is at x = 50 + 1.7 = 51.7, y = 12
    draw_path_arrow([(51.9, 57), (87, 57), (87, 12), (51.7, 12)])
    ax.text(69.5, 58.4, "[traceability verified / compliant]", fontsize=8.8, ha='center', va='bottom', family='sans-serif')

    # 6. Final Node: Bullseye
    draw_end_node(50, 12, r_outer=1.7, r_inner=1.05)

    # Save outputs
    os.makedirs(r"docs\diagrams\activity", exist_ok=True)
    png_path = r"docs\diagrams\activity\activity_diagram.png"
    svg_path = r"docs\diagrams\activity\activity_diagram.svg"

    plt.tight_layout()
    plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor=C_WHITE)
    plt.savefig(svg_path, bbox_inches='tight', facecolor=C_WHITE)
    plt.close()

    print(f"Generated Reference-Style PNG: {png_path}")
    print(f"Generated Reference-Style SVG: {svg_path}")

if __name__ == '__main__':
    create_reference_activity_diagram()

