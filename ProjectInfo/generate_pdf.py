"""
Script to generate a clean, professional PDF and PNG guide
explaining the 7-Level Architecture, OS & DBMS mapping, and folder breakdown.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "ProjectInfo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_FILE = OUTPUT_DIR / "SmartTraffic_Architecture_and_Modules.pdf"


def generate_pdf():
    doc = SimpleDocTemplate(
        str(PDF_FILE),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0f766e'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=12,
        spaceAfter=4
    )
    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b')
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    story = []

    # Title Banner
    story.append(Paragraph("Smart Traffic Management System", title_style))
    story.append(Paragraph("7-Level System Architecture, OS & DBMS Module Mapping, and Viva Guide<br/>Team StructMinds (Ayush Gaur, Vedansh Manwal, Anmol Pujari)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceAfter=12))

    # Section 1: Approach Validation
    story.append(Paragraph("1. Approach Verification: 100% Match to 7-Level Pipeline", h2_style))
    story.append(Paragraph(
        "Our implementation follows the exact hierarchical model designed for this project. "
        "The simulation flows from environment sensing down to decision arbitration, actuation, and persistent database logging.",
        body_style
    ))

    # Level Table
    data = [
        [Paragraph("Level", table_header), Paragraph("Module Name", table_header), Paragraph("Exact File Location", table_header), Paragraph("Technical Responsibility", table_header)],
        [Paragraph("<b>Level 1</b>", table_text), Paragraph("Simulation Environment", table_text), Paragraph("TrafficControl/network.net.xml<br/>TrafficControl/routes.rou.xml", table_text), Paragraph("Builds microscopic 4-way left-hand intersection and vehicle routes in SUMO.", table_text)],
        [Paragraph("<b>Level 2</b>", table_text), Paragraph("Main Controller", table_text), Paragraph("src/simulation/sumo_env.py<br/>main.py / gui_app.py", table_text), Paragraph("Python TraCI bridge extracting vehicle counts, speeds, waiting times, and queues.", table_text)],
        [Paragraph("<b>Level 3A</b>", table_text), Paragraph("AI Core Module (DQN)", table_text), Paragraph("src/rl/dqn_agent.py<br/>src/rl/train_dqn.py", table_text), Paragraph("PyTorch Deep Q-Network observing states and recommending green phase actions.", table_text)],
        [Paragraph("<b>Level 3B</b>", table_text), Paragraph("OS Layer (Scheduler)", table_text), Paragraph("src/scheduling/scheduler.py", table_text), Paragraph("Real-time Dynamic Priority scheduling, Aging, and anti-starvation counters.", table_text)],
        [Paragraph("<b>Level 4</b>", table_text), Paragraph("Decision & Safety Layer", table_text), Paragraph("src/simulation/signal_controller.py<br/>scheduler.py (arbitrate)", table_text), Paragraph("Guarantees safe clearance: min green (10s), max green (60s), 3s yellow, OS veto.", table_text)],
        [Paragraph("<b>Level 5</b>", table_text), Paragraph("Action Implementation", table_text), Paragraph("src/simulation/sumo_env.py", table_text), Paragraph("Applies validated signal states directly to junction C in SUMO via TraCI.", table_text)],
        [Paragraph("<b>Level 6</b>", table_text), Paragraph("Data Persistence (DBMS)", table_text), Paragraph("src/database/db_manager.py", table_text), Paragraph("Stores runs, metrics, and decisions in MySQL (with auto SQLite fallback).", table_text)],
        [Paragraph("<b>Level 7</b>", table_text), Paragraph("Analysis & Metrics", table_text), Paragraph("src/evaluation/evaluator.py<br/>src/evaluation/plot_results.py", table_text), Paragraph("Computes throughput, delay, max queue, and exports comparison charts.", table_text)],
    ]

    t = Table(data, colWidths=[50, 110, 180, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Section 2: OS Module
    story.append(Paragraph("2. Where Operating Systems (OS) Concepts Are Implemented", h2_style))
    story.append(Paragraph("<b>Primary Code File:</b> <font color='#0f766e'>src/scheduling/scheduler.py</font>", body_style))
    story.append(Paragraph("• <b>Ready Processes:</b> Directional traffic approaches (NS and EW flows) are instances of <i>TrafficProcess</i> with dynamic queues and state.", bullet_style))
    story.append(Paragraph("• <b>CPU Time Slice:</b> Signal green time is treated as CPU execution quantum constrained by min green (10s) and max green (60s).", bullet_style))
    story.append(Paragraph("• <b>Dynamic Priority:</b> <i>Priority = (Queue Length * w_q) + (Starvation Time * w_a)</i>. Bounded waiting is maintained dynamically.", bullet_style))
    story.append(Paragraph("• <b>Process Aging:</b> Time spent waiting without green light increments <i>time_starved</i> every second, boosting priority to prevent starvation.", bullet_style))
    story.append(Paragraph("• <b>Kernel Arbiter / Veto:</b> The <i>arbitrate()</i> function inspects the AI agent's proposals. If a direction exceeds max starvation (45s), the OS layer vetoes the AI.", bullet_style))
    story.append(Paragraph("• <b>Context Switch Cost:</b> Mandatory 3-second yellow clearance represents context-switch overhead, preventing high-frequency thrashing.", bullet_style))

    # Section 3: DBMS Module
    story.append(Paragraph("3. Where Database Management (DBMS) Is Implemented", h2_style))
    story.append(Paragraph("<b>Primary Code File:</b> <font color='#0f766e'>src/database/db_manager.py</font> | <b>Storage:</b> <font color='#0f766e'>results/traffic_results.sqlite3</font>", body_style))
    story.append(Paragraph("• <b>Normalized Relational Schema:</b> Three distinct relational tables with primary and foreign keys:", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>simulation_runs</i>: Summary metrics (run_id PK, controller, arrived, stopped_veh_sec, CO2, throughput).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>step_metrics</i>: Second-by-second traffic observations (run_id FK, sim_time, active_vehicles, halted, queues).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>scheduler_decisions</i>: OS & AI arbitration audit logs (run_id FK, chosen_phase, reason, waiting times).", bullet_style))
    story.append(Paragraph("• <b>ACID Transactions & Parameterized Queries:</b> Parameterized SQL queries prevent injection and ensure atomic <i>commit()</i> / <i>rollback()</i>.", bullet_style))
    story.append(Paragraph("• <b>Dual Driver Architecture:</b> Production-ready MySQL connection with automated zero-crash fallback to SQLite for local presentations.", bullet_style))

    # Section 4: Folder Organization
    story.append(Paragraph("4. Clean Project Directory Structure", h2_style))
    story.append(Paragraph("The directory has been cleaned to keep strictly the essential, demonstrable modules:", body_style))
    story.append(Paragraph("• <b>run_dashboard.bat & gui_app.py:</b> Desktop visual dashboard with live terminal logs, seed selector, and auto-zoomed SUMO visualizer.", bullet_style))
    story.append(Paragraph("• <b>main.py:</b> Unified CLI entry point for scripted benchmarks, single runs, and training.", bullet_style))
    story.append(Paragraph("• <b>TrafficControl/:</b> SUMO simulation network files, route demand, and viewsettings.xml (auto-zoom + real-world scheme).", bullet_style))
    story.append(Paragraph("• <b>src/scheduling/:</b> OS Process Scheduling (TrafficProcess, Priority, Aging, Arbitration).", bullet_style))
    story.append(Paragraph("• <b>src/rl/:</b> Deep Q-Network agent (PyTorch policy and target networks, experience replay).", bullet_style))
    story.append(Paragraph("• <b>src/simulation/:</b> TraCI Gym-like environment and SignalController safety interval manager.", bullet_style))
    story.append(Paragraph("• <b>src/database/:</b> MySQL / SQLite persistence and transactional storage.", bullet_style))
    story.append(Paragraph("• <b>src/evaluation/:</b> 4-controller benchmarking engine and comparison chart plotter.", bullet_style))
    story.append(Paragraph("• <b>tests/:</b> 10 automated unit tests (test_traffic_system.py) verifying safety, OS, AI, and DBMS.", bullet_style))
    story.append(Paragraph("• <b>results/:</b> benchmark_comparison.png and traffic_results.sqlite3.", bullet_style))
    story.append(Paragraph("• <b>ProjectInfo/:</b> This architecture documentation and viva reference guide.", bullet_style))

    doc.build(story)
    print(f"[PDF Generator] Successfully created PDF at {PDF_FILE}")


if __name__ == "__main__":
    generate_pdf()
