import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_dfd_level_1():
    fig, ax = plt.subplots(figsize=(18, 12), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')

    # Draw subtle background grid
    for x in range(0, 101, 2):
        ax.axvline(x, color='#f0f0f0', linewidth=0.6, zorder=0)
    for y in range(0, 101, 2):
        ax.axhline(y, color='#f0f0f0', linewidth=0.6, zorder=0)

    # -------------------------------------------------------------
    # Title & Level Tag
    # -------------------------------------------------------------
    rect_lvl = patches.Rectangle((3, 93), 8, 4, facecolor='white', edgecolor='black', linewidth=1.8, zorder=3)
    ax.add_patch(rect_lvl)
    ax.text(7, 95, "Level 1", fontsize=11, fontweight='bold', ha='center', va='center', family='sans-serif')

    ax.text(50, 95.5, "LEVEL 1 DATA FLOW DIAGRAM - ORION", fontsize=15, fontweight='bold', ha='center', va='center', family='sans-serif')
    ax.text(50, 93, "(Automated Requirements Traceability and Test Coverage Mapper)", fontsize=10.5, ha='center', va='center', family='sans-serif')

    # -------------------------------------------------------------
    # Helper Draw Functions
    # -------------------------------------------------------------
    def draw_entity(x, y, w, h, text):
        rect = patches.Rectangle((x - w/2, y - h/2), w, h, facecolor='white', edgecolor='black', linewidth=1.8, zorder=3)
        ax.add_patch(rect)
        ax.text(x, y, text, fontsize=9.5, fontweight='bold', ha='center', va='center', family='sans-serif')

    def draw_process(x, y, r, num, text):
        circle = patches.Circle((x, y), r, facecolor='white', edgecolor='black', linewidth=1.8, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y + 2.0, num, fontsize=10, fontweight='bold', ha='center', va='center', family='sans-serif')
        ax.text(x, y - 1.2, text, fontsize=8.2, ha='center', va='center', family='sans-serif')

    def draw_store(x, y, w, h, store_id, name):
        id_w = 4.5
        rect_id = patches.Rectangle((x, y - h/2), id_w, h, facecolor='white', edgecolor='black', linewidth=1.8, zorder=3)
        ax.add_patch(rect_id)
        ax.text(x + id_w/2, y, store_id, fontsize=9.5, fontweight='bold', ha='center', va='center', family='sans-serif')

        # Open body (top line, bottom line, left closed)
        ax.plot([x + id_w, x + w], [y + h/2, y + h/2], color='black', linewidth=1.8, zorder=3)
        ax.plot([x + id_w, x + w], [y - h/2, y - h/2], color='black', linewidth=1.8, zorder=3)
        fill_rect = patches.Rectangle((x + id_w, y - h/2 + 0.1), w - id_w, h - 0.2, facecolor='white', edgecolor='none', zorder=2)
        ax.add_patch(fill_rect)
        ax.text(x + id_w + (w - id_w)/2, y, name, fontsize=9.5, fontweight='bold', ha='center', va='center', family='sans-serif')

    # Draw Entities
    draw_entity(10, 80, 11, 7, "Jira Cloud")
    draw_entity(10, 60, 12, 7.5, "GitHub\nRepository")
    draw_entity(12, 28, 12, 7.5, "QA Lead /\nAdmin")
    draw_entity(88, 12, 13, 7.5, "Developer /\nReviewer")

    # Draw Processes
    draw_process(42, 80, 5.5, "1.0", "Ingest & Parse\nRequirements")
    draw_process(42, 60, 5.5, "2.0", "Extract Test Code\n& Assertions")
    draw_process(57, 47, 7.0, "3.0", "Match Requirements\nto Test Cases\n(Semantic & Structural)")
    draw_process(45, 28, 6.2, "4.0", "Hybrid Risk Engine\n& Classification")
    draw_process(52, 12, 6.5, "5.0", "Reporting, CI/CD\nGating & Notification\nService")

    # Draw Stores (Shifted slightly right so arrows breathe)
    draw_store(70, 80, 24, 5.5, "D1", "Requirements Store")
    draw_store(70, 64, 24, 5.5, "D2", "Test Case Store")
    draw_store(76, 47, 21, 5.5, "D3", "Traceability Matrix Store")
    draw_store(65, 28, 22, 5.5, "D4", "Risk & Analysis Store")

    # -------------------------------------------------------------
    # Helper Arrow Function
    # -------------------------------------------------------------
    def draw_path(pts, label="", label_pos=None, label_ha='center', label_va='bottom'):
        for i in range(len(pts) - 1):
            if i == len(pts) - 2:
                ax.annotate(
                    '',
                    xy=pts[i+1],
                    xytext=pts[i],
                    arrowprops=dict(arrowstyle="-|>", color='black', lw=1.4, mutation_scale=12),
                    zorder=4
                )
            else:
                ax.plot([pts[i][0], pts[i+1][0]], [pts[i][1], pts[i+1][1]], color='black', lw=1.4, zorder=4)

        if label and label_pos:
            ax.text(label_pos[0], label_pos[1], label, fontsize=7.8, ha=label_ha, va=label_va,
                    bbox=dict(boxstyle='square,pad=0.2', facecolor='white', edgecolor='none', alpha=0.95),
                    zorder=5, family='sans-serif')

    # -------------------------------------------------------------
    # Connecting Flows (Strictly verified)
    # -------------------------------------------------------------

    # 1. Jira -> 1.0
    draw_path([(15.5, 80), (36.5, 80)], "Requirements\n(Issues, Updates)", (26, 80.8))

    # 2. 1.0 -> D1
    draw_path([(47.5, 80), (70, 80)], "Parsed Requirements Data", (58.5, 80.8))

    # 3. GitHub -> 2.0
    draw_path([(16, 60), (36.5, 60)], "Test Code / PR Events\n(Webhooks)", (26, 60.8))

    # 4. 2.0 -> D2 (Correct write to D2!)
    draw_path([(47.5, 60), (58, 60), (58, 64), (70, 64)], "Parsed Test Data", (61, 64.8))

    # 5. D1 -> 3.0 (Clean curve to 3.0 without touching D2)
    draw_path([(67, 80), (64, 80), (64, 53.5)], "Requirements Data", (64, 72), label_ha='right')

    # 6. D2 -> 3.0 (Test Data & Assertions)
    draw_path([(73, 61.2), (73, 52), (63.8, 50)], "Test Data & Assertions", (73, 55), label_ha='left')

    # 7. 3.0 -> D3 (Traceability Mappings)
    draw_path([(64, 47), (76, 47)], "Traceability Mappings", (70, 47.7))

    # 8. D2 -> 4.0 (Extracted AST Assertion Tuples - MATCHES LEVEL 2)
    draw_path([(88, 61.2), (88, 38), (49, 38), (49, 34)], "Extracted AST Assertion Tuples", (70, 38.8))

    # 9. D3 -> 4.0 (Mappings & Overlap Scores)
    draw_path([(84, 44.2), (84, 34), (50.5, 30.5)], "Mappings & Overlap Scores", (74, 34.8))

    # 10. QA Lead -> 4.0
    draw_path([(18, 28), (38.8, 28)], "Risk Configuration\n(Thresholds, Rules)", (28, 28.8))

    # 11. 4.0 -> D4
    draw_path([(51.2, 28), (65, 28)], "Risk Results", (58, 28.8))

    # 12. 4.0 -> 5.0
    draw_path([(47, 21.8), (49, 18.2)], "Risk Data &\nAttributions", (44.5, 19.5))

    # 13. D4 -> 5.0
    draw_path([(73, 25.2), (73, 16), (58.5, 14)], "Stored Risk Reports", (70, 18.5))

    # 14. D3 -> 5.0
    draw_path([(94, 44.2), (94, 22), (63, 22), (58.5, 15)], "Matrix Data", (94, 30), label_ha='left')

    # 15. Dev -> 5.0 (Review Request)
    draw_path([(81.5, 13.5), (58.5, 13.5)], "Review Request\n(Traceability Query)", (70, 14.3))

    # 16. 5.0 -> Dev (Traceability Results)
    draw_path([(58.5, 10.5), (81.5, 10.5)], "Traceability Results\n(RTM, Risk Status)", (70, 7.8))

    # 17. 5.0 -> QA Lead (Reports)
    draw_path([(45.5, 12), (12, 12), (12, 24.2)], "RTM & Risk Reports\n(Dashboard, Analysis)", (25, 12.7))

    # 18. 5.0 -> GitHub (Check Run Results - MATCHES LEVEL 0)
    draw_path([(46, 9.5), (7, 9.5), (7, 56.2)], "Check Run Results\n(PR Status, Annotations)", (23, 7.2))

    # 19. 5.0 -> Jira (Drift Alerts)
    draw_path([(47, 6.5), (4, 6.5), (4, 80), (4.5, 80)], "Drift Alerts\n(Comments, Status Updates)", (22, 4.2))

    plt.tight_layout()
    output_path = r"d:\PROJECTS\ORION\Level_1_DFD_ORION_Corrected.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("Regenerated cleanly to", output_path)

if __name__ == '__main__':
    draw_dfd_level_1()
