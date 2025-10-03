import streamlit as st
import json
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob

# Configure page to always use wide mode and hide sidebar
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Note: load_data function removed since we only use cohort_labels.jsonl

def load_cohort_labels_data():
    """Load the cohort_labels.jsonl data with different structure"""
    data = []
    try:
        with open('notebooks/out_synthrad/cohort.jsonl', 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                try:
                    record = json.loads(line)
                    # Validate that the record has the expected structure
                    if 'patient_id' in record and 'study_date' in record:
                        data.append(record)
                    else:
                        st.warning(f"Line {line_num}: Missing required fields (patient_id, study_date)")
                except json.JSONDecodeError as e:
                    st.error(f"Error parsing JSON line {line_num}: {e}")
                    continue
    except FileNotFoundError:
        st.error("Could not find cohort_labels.jsonl file")
        return []
    
    if data:
        st.toast(f"Successfully loaded {len(data)} records from cohort_labels.jsonl")
        # Check if reports are embedded
        records_with_reports = sum(1 for record in data if record.get('report_text'))
        if records_with_reports > 0:
            st.toast(f"📄 {records_with_reports}/{len(data)} records contain embedded report text")
        else:
            st.toast("⚠️ No embedded report text found - will use fallback file reading")
    
    return data

def validate_jsonl_structure(data):
    """Validate and display information about the JSONL data structure"""
    if not data:
        return
    
    st.subheader("📊 Data Structure Analysis")
    
    # Check for embedded reports
    records_with_reports = sum(1 for record in data if record.get('report_text'))
    total_records = len(data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Records", total_records)
    
    with col2:
        st.metric("Records with Reports", records_with_reports)
    
    with col3:
        report_coverage = (records_with_reports / total_records * 100) if total_records > 0 else 0
        st.metric("Report Coverage", f"{report_coverage:.1f}%")
    
    # Check for primary tumors and tumor type detection
    st.subheader("🔍 Tumor Type Analysis")
    primary_tumor_count = 0
    lung_primary_count = 0
    unknown_tumor_count = 0
    
    for record in data:
        lesions = record.get('lesions', [])
        has_primary = any(lesion.get('kind') == 'primary' for lesion in lesions)
        if has_primary:
            primary_tumor_count += 1
            # Check if it's lung
            for lesion in lesions:
                if lesion.get('kind') == 'primary' and lesion.get('organ') == 'lung':
                    lung_primary_count += 1
                    break
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Records with Primary Tumors", primary_tumor_count)
    with col2:
        st.metric("Lung Primary Tumors", lung_primary_count)
    with col3:
        st.metric("Expected Lung Cancer Cases", lung_primary_count)
    
    
    # Show available fields
    if data:
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())
        
        st.subheader("Available Fields")
        st.write("• " + " • ".join(sorted(all_fields)))

def find_report_text(patient_id, timepoint):
    """Find the corresponding report text file in out_synthrad directory (fallback method)"""
    
    # Construct the path pattern
    study_dir = f"study_{timepoint + 1:02d}"
    pattern = f"notebooks/out_synthrad/{patient_id}/{study_dir}/*.txt"
    
    # Find matching text files
    txt_files = glob.glob(pattern)
    
    if txt_files:
        # Read the first matching text file
        try:
            with open(txt_files[0], 'r') as f:
                return f.read().strip()
        except Exception as e:
            return f"Error reading report: {e}"
    
    return f"No report found for {patient_id} study {timepoint + 1}"

def convert_cohort_labels_to_standard_format(cohort_labels_data):
    """Convert cohort_labels.jsonl format to standard format for visualization"""
    converted_data = []
    
    for record in cohort_labels_data:
        # Extract basic info
        patient_id = record.get('patient_id', 'Unknown')
        study_date = record.get('study_date', '')
        timepoint = record.get('timepoint', 0)
        
        # Create study_id
        study_id = f"{patient_id}_S{timepoint + 1}"
        
        # Get report text from JSONL data (preferred) or fallback to file reading
        report_text = record.get('report_text', '')
        if not report_text or report_text.strip() == '':
            # Fallback to reading from file if report_text not in JSONL or is empty
            report_text = find_report_text(patient_id, timepoint)
            if report_text.startswith("No report found") or report_text.startswith("Error reading"):
                # If file reading also fails, provide a placeholder
                report_text = f"[Report text not available for {patient_id} study {timepoint + 1}]"
        
        # Extract lesion data
        lesions = record.get('lesions', [])
        target_lesions = []
        non_target_lesions = []
        primary_tumor = None
        
        for lesion in lesions:
            lesion_data = {
                'lesion_id': lesion.get('lesion_id', 'Unknown'),
                'site': lesion.get('location', lesion.get('station', 'Unknown')),
                'description': f"{lesion.get('kind', 'Unknown')} - {lesion.get('organ', 'Unknown')}",
                'measurable': lesion.get('target', False),
                'dimensions_mm': [lesion.get('size_mm_current', 0), lesion.get('size_mm_current', 0)],
                'series_image': f"timepoint_{timepoint}"
            }
            
            # Add baseline and follow-up data if available
            if lesion.get('baseline_mm') is not None:
                lesion_data['baseline_dimensions_mm'] = [lesion.get('baseline_mm', 0), lesion.get('baseline_mm', 0)]
            if lesion.get('follow_mm') is not None:
                lesion_data['follow_dimensions_mm'] = [lesion.get('follow_mm', 0), lesion.get('follow_mm', 0)]
            
            # Categorize lesions
            if lesion.get('kind') == 'primary':
                primary_tumor = {
                    'organ': lesion.get('organ', 'Unknown'),
                    'site': lesion.get('location', 'Unknown'),
                    'dimensions_mm': [lesion.get('size_mm_current', 0), lesion.get('size_mm_current', 0)],
                    'max_thickness_mm': lesion.get('size_mm_current', 0)
                }
                if lesion.get('target', False):
                    target_lesions.append(lesion_data)
            elif lesion.get('target', False):
                target_lesions.append(lesion_data)
            else:
                non_target_lesions.append(lesion_data)
        
        # Create annotations structure
        annotations = {
            'target_lesions': target_lesions,
            'non_target_lesions': non_target_lesions,
            'recist': {
                'timepoint': 'baseline' if timepoint == 0 else 'follow_up',
                'sum_mm': record.get('current_sld_mm', 0),
                'baseline_sum_mm': record.get('baseline_sld_mm', 0)
            }
        }
        
        # Add primary tumor if found
        if primary_tumor:
            annotations['primary_tumor'] = primary_tumor
        
        # All cases are lung cancer
        tumor_type = "non-small cell lung carcinoma"
        
        # Use existing staging information from JSONL data if available
        existing_staging = record.get('staging', {})
        
        if existing_staging:
            # Use the staging data directly from the JSONL
            t_stage = existing_staging.get('T', 'TX')
            n_stage = existing_staging.get('N', 'N0')
            m_stage = existing_staging.get('M', 'M0')
            stage_group = existing_staging.get('stage_group', 'Unknown')
            
            staging = {
                't_stage': t_stage,
                'n_stage': n_stage,
                'm_stage': m_stage,
                'tnm_stage': f'{t_stage} {n_stage} {m_stage}',
                'stage_group': stage_group,
                'recist_category': record.get('overall_response', 'Unknown'),
                'recist_percent_change': None
            }
        else:
            # Fallback to dynamic TNM staging based on available data (if no staging data in JSONL)
            # T stage: Based on primary tumor size with detailed subcategories
            t_stage = 'TX'  # Default unknown
            if primary_tumor:
                max_dimension = max(primary_tumor.get('dimensions_mm', [0, 0]))
                if max_dimension <= 20:
                    t_stage = 'T1a'
                elif max_dimension <= 30:
                    t_stage = 'T1b'
                elif max_dimension <= 50:
                    t_stage = 'T2a'
                elif max_dimension <= 70:
                    t_stage = 'T2b'
                elif max_dimension <= 80:
                    t_stage = 'T3'
                else:
                    t_stage = 'T4'
            
            # N stage: Based on lymph node involvement with detailed subcategories
            n_stage = 'N0'  # Default no lymph node involvement
            lymph_node_lesions = [l for l in lesions if 'lymph' in l.get('site', '').lower() or 'node' in l.get('site', '').lower() or 'ln_' in l.get('lesion_id', '').lower()]
            if lymph_node_lesions:
                # Count ipsilateral lymph nodes
                ipsilateral_nodes = [l for l in lymph_node_lesions if 'R' in l.get('site', '') or 'right' in l.get('site', '').lower()]
                contralateral_nodes = [l for l in lymph_node_lesions if 'L' in l.get('site', '') or 'left' in l.get('site', '').lower()]
                
                if len(ipsilateral_nodes) == 1:
                    n_stage = 'N1'
                elif len(ipsilateral_nodes) >= 2 or len(contralateral_nodes) > 0:
                    n_stage = 'N2'
                elif len(lymph_node_lesions) >= 4:
                    n_stage = 'N3'
            
            # M stage: Based on distant metastases with detailed subcategories
            m_stage = 'M0'  # Default no distant metastases
            distant_lesions = [l for l in lesions if l.get('organ', '').lower() not in ['lung', 'lymph'] and 'ln_' not in l.get('lesion_id', '').lower()]
            if distant_lesions:
                # Check for specific metastatic sites
                adrenal_lesions = [l for l in distant_lesions if 'adrenal' in l.get('organ', '').lower() or 'adrenal' in l.get('site', '').lower()]
                bone_lesions = [l for l in distant_lesions if 'bone' in l.get('organ', '').lower() or 'bone' in l.get('site', '').lower()]
                brain_lesions = [l for l in distant_lesions if 'brain' in l.get('organ', '').lower() or 'brain' in l.get('site', '').lower()]
                
                if len(distant_lesions) == 1:
                    m_stage = 'M1a' if adrenal_lesions else 'M1b'
                elif len(distant_lesions) >= 2:
                    m_stage = 'M1b'
                elif brain_lesions:
                    m_stage = 'M1c'
            
            # Calculate overall stage group
            stage_group = 'Unknown'
            if t_stage != 'TX' and n_stage != 'NX' and m_stage != 'MX':
                if m_stage.startswith('M1'):
                    stage_group = 'IV'
                elif t_stage.startswith('T1') and n_stage == 'N0':
                    stage_group = 'I'
                elif t_stage.startswith('T2') and n_stage == 'N0':
                    stage_group = 'II'
                elif t_stage.startswith('T1') and n_stage in ['N1', 'N2']:
                    stage_group = 'IIIA'
                elif t_stage.startswith('T2') and n_stage in ['N1', 'N2']:
                    stage_group = 'IIIB'
                elif t_stage in ['T3', 'T4']:
                    stage_group = 'IIIB'
            
            staging = {
                't_stage': t_stage,
                'n_stage': n_stage,
                'm_stage': m_stage,
                'tnm_stage': f'{t_stage} {n_stage} {m_stage}',
                'stage_group': stage_group,
                'recist_category': record.get('overall_response', 'Unknown'),
                'recist_percent_change': None
            }
        
        # Calculate percent change if we have baseline and current SLD
        baseline_sld = record.get('baseline_sld_mm', 0)
        current_sld = record.get('current_sld_mm', 0)
        if baseline_sld and current_sld and baseline_sld > 0:
            percent_change = ((current_sld - baseline_sld) / baseline_sld) * 100
            staging['recist_percent_change'] = round(percent_change, 1)
        
        annotations['staging'] = staging
        
        # Create standard format record
        converted_record = {
            'patient_id': patient_id,
            'study_id': study_id,
            'exam_date': study_date,
            'tumor_type': tumor_type,
            'modality': 'CT chest abdomen pelvis with IV contrast',  # Default
            'report_text': report_text,  # Use the actual report text from file
            'annotations': annotations
        }
        
        converted_data.append(converted_record)
    
    return converted_data

def prepare_longitudinal_data(patient_studies):
    """Prepare data for longitudinal visualization"""
    longitudinal_data = []
    
    for study in patient_studies:
        exam_date = datetime.strptime(study['exam_date'], '%Y-%m-%d')
        annotations = study['annotations']
        
        # Extract target lesions
        if 'target_lesions' in annotations:
            for lesion in annotations['target_lesions']:
                if 'dimensions_mm' in lesion:
                    # Calculate lesion area (approximate)
                    dimensions = lesion['dimensions_mm']
                    area = (dimensions[0] * dimensions[1] * np.pi) / 4  # Ellipse area approximation
                    
                    longitudinal_data.append({
                        'study_id': study['study_id'],
                        'exam_date': exam_date,
                        'exam_date_str': study['exam_date'],
                        'lesion_id': lesion.get('lesion_id', 'Unknown'),
                        'site': lesion.get('site', 'Unknown'),
                        'length_mm': dimensions[0],
                        'width_mm': dimensions[1],
                        'area_mm2': area,
                        'max_dimension': max(dimensions),
                        'suv_max': lesion.get('suv_max'),
                        'change': lesion.get('change', 'baseline')
                    })
        
        # Extract RECIST data
        if 'recist' in annotations and annotations['recist'].get('sum_mm'):
            longitudinal_data.append({
                'study_id': study['study_id'],
                'exam_date': exam_date,
                'exam_date_str': study['exam_date'],
                'lesion_id': 'RECIST_SUM',
                'site': 'All Target Lesions',
                'length_mm': None,
                'width_mm': None,
                'area_mm2': None,
                'max_dimension': annotations['recist']['sum_mm'],
                'suv_max': None,
                'change': annotations['recist'].get('timepoint', 'baseline')
            })
    
    return pd.DataFrame(longitudinal_data)

def create_lesion_size_chart(df, lesion_type='all'):
    """Create interactive lesion size chart"""
    if df.empty:
        return None
    
    # Filter data based on lesion type
    if lesion_type == 'target_lesions':
        chart_df = df[df['lesion_id'] != 'RECIST_SUM'].copy()
    elif lesion_type == 'recist_sum':
        chart_df = df[df['lesion_id'] == 'RECIST_SUM'].copy()
    else:
        chart_df = df.copy()
    
    if chart_df.empty:
        return None
    
    # Create the chart
    fig = go.Figure()
    
    # Add traces for each lesion
    for lesion_id in chart_df['lesion_id'].unique():
        lesion_data = chart_df[chart_df['lesion_id'] == lesion_id].sort_values('exam_date')
        
        if lesion_id == 'RECIST_SUM':
            fig.add_trace(go.Scatter(
                x=lesion_data['exam_date'],
                y=lesion_data['max_dimension'],
                mode='lines+markers',
                name=f'{lesion_id} (Sum)',
                line=dict(width=4, color='red'),
                marker=dict(size=8),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            'Date: %{x}<br>' +
                            'Sum: %{y} mm<br>' +
                            '<extra></extra>'
            ))
        else:
            # Add length and width traces
            fig.add_trace(go.Scatter(
                x=lesion_data['exam_date'],
                y=lesion_data['length_mm'],
                mode='lines+markers',
                name=f'{lesion_id} - Length',
                line=dict(dash='solid'),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            'Date: %{x}<br>' +
                            'Length: %{y} mm<br>' +
                            '<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=lesion_data['exam_date'],
                y=lesion_data['width_mm'],
                mode='lines+markers',
                name=f'{lesion_id} - Width',
                line=dict(dash='dash'),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            'Date: %{x}<br>' +
                            'Width: %{y} mm<br>' +
                            '<extra></extra>'
            ))
    
    fig.update_layout(
        title='Lesion Size Over Time',
        xaxis_title='Exam Date',
        yaxis_title='Size (mm)',
        hovermode='x unified',
        height=400
    )
    
    return fig

def create_lesion_area_chart(df):
    """Create lesion area comparison chart"""
    target_lesions = df[df['lesion_id'] != 'RECIST_SUM'].copy()
    
    if target_lesions.empty:
        return None
    
    fig = px.area(
        target_lesions, 
        x='exam_date', 
        y='area_mm2', 
        color='lesion_id',
        title='Lesion Area Over Time',
        labels={'area_mm2': 'Area (mm²)', 'exam_date': 'Exam Date'},
        height=400
    )
    
    fig.update_layout(hovermode='x unified')
    return fig

def create_timeline_view(patient_studies):
    """Create timeline view of all studies"""
    timeline_data = []
    
    for study in patient_studies:
        exam_date = datetime.strptime(study['exam_date'], '%Y-%m-%d')
        annotations = study['annotations']
        
        # Count lesions
        target_count = len(annotations.get('target_lesions', []))
        non_target_count = len(annotations.get('non_target_lesions', []))
        
        timeline_data.append({
            'study_id': study['study_id'],
            'exam_date': exam_date,
            'exam_date_str': study['exam_date'],
            'modality': study['modality'],
            'tumor_type': study['tumor_type'],
            'target_lesions': target_count,
            'non_target_lesions': non_target_count,
            'recist_sum': annotations.get('recist', {}).get('sum_mm', 0)
        })
    
    timeline_df = pd.DataFrame(timeline_data).sort_values('exam_date')
    
    # Create timeline chart
    fig = go.Figure()
    
    # Add study points
    fig.add_trace(go.Scatter(
        x=timeline_df['exam_date'],
        y=[1] * len(timeline_df),
        mode='markers+text',
        marker=dict(size=15, color='blue'),
        text=timeline_df['study_id'],
        textposition='top center',
        name='Studies',
        hovertemplate='<b>%{text}</b><br>' +
                     'Date: %{x}<br>' +
                     'Modality: ' + timeline_df['modality'] + '<br>' +
                     'Target Lesions: ' + timeline_df['target_lesions'].astype(str) + '<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title='Study Timeline',
        xaxis_title='Date',
        yaxis=dict(showticklabels=False, range=[0.5, 1.5]),
        height=200,
        showlegend=False
    )
    
    return fig, timeline_df

def get_stage_color(stage):
    """Get color for TNM stage"""
    if not stage:
        return "gray"
    stage = stage.upper().strip()
    
    # Handle stage groups (I, II, IIIA, IIIB, IV)
    if stage.startswith("IV"):
        return "purple"
    elif stage.startswith("IIIB"):
        return "red"
    elif stage.startswith("IIIA"):
        return "orange"
    elif stage.startswith("III"):
        return "red"
    elif stage.startswith("II"):
        return "orange"
    elif stage.startswith("I"):
        return "green"
    
    # Handle individual TNM components
    elif "M1" in stage:
        return "purple"  # Metastatic disease
    elif "T4" in stage or "N3" in stage or "N2" in stage:
        return "red"     # Advanced local disease
    elif "T3" in stage or "T2" in stage or "N1" in stage:
        return "orange"  # Intermediate disease
    elif "T1" in stage or "N0" in stage:
        return "green"   # Early stage disease
    
    return "gray"

def determine_recist_response(sld_now, new_lesion, baseline_sld):
    """Determine RECIST response category"""
    if new_lesion:
        return "PD"
    if sld_now == 0:
        return "CR"
    if baseline_sld and sld_now <= 0.7 * baseline_sld:  # ≥30% decrease
        return "PR"
    if baseline_sld and sld_now >= 1.2 * baseline_sld and (sld_now - baseline_sld) >= 5:  # ≥20% increase
        return "PD"
    return "SD"

def create_patient_course_visualization(patient_studies, patient_id):
    """Create comprehensive patient course visualization with lesions, SLD, and TNM staging"""
    if not patient_studies:
        return None
    
    # Sort studies by date
    sorted_studies = sorted(patient_studies, key=lambda x: x['exam_date'])
    
    # Extract data
    dates = [datetime.strptime(study['exam_date'], '%Y-%m-%d') for study in sorted_studies]
    dates_str = [study['exam_date'] for study in sorted_studies]
    
    # Get baseline data
    baseline_study = sorted_studies[0]
    baseline_sld = baseline_study['annotations'].get('recist', {}).get('sum_mm', 0)
    
    # Collect all lesion data - use the same approach as the matplotlib example
    all_lesion_ids = set()
    baseline_targets = set()
    
    # First pass: collect all lesion IDs and identify baseline targets
    for study in sorted_studies:
        annotations = study['annotations']
        
        # Primary tumor
        primary_tumor = annotations.get('primary_tumor', {})
        if primary_tumor:
            all_lesion_ids.add('Primary_Tumor')
            baseline_targets.add('Primary_Tumor')
        
        # Target lesions
        for lesion in annotations.get('target_lesions', []):
            lesion_id = lesion.get('lesion_id', 'Unknown')
            all_lesion_ids.add(lesion_id)
            if study == baseline_study:  # Only add to baseline targets from first study
                baseline_targets.add(lesion_id)
        
        # Non-target lesions
        for lesion in annotations.get('non_target_lesions', []):
            lesion_id = lesion.get('lesion_id', 'Unknown')
            all_lesion_ids.add(lesion_id)
    
    # Second pass: collect lesion series data
    lesion_series = {}
    for lesion_id in sorted(all_lesion_ids):
        lesion_series[lesion_id] = []
        
        for study in sorted_studies:
            study_date = study['exam_date']
            annotations = study['annotations']
            size = np.nan  # Default to NaN if not found
            
            # Check primary tumor
            if lesion_id == 'Primary_Tumor':
                primary_tumor = annotations.get('primary_tumor', {})
                if primary_tumor:
                    if 'dimensions_mm' in primary_tumor:
                        dimensions = primary_tumor['dimensions_mm']
                        size = max(dimensions) if dimensions else 0
                    elif 'max_thickness_mm' in primary_tumor:
                        size = primary_tumor['max_thickness_mm']
                    elif 'soft_tissue_thickness_mm' in primary_tumor:
                        size = primary_tumor['soft_tissue_thickness_mm']
            
            # Check target lesions
            for lesion in annotations.get('target_lesions', []):
                if lesion.get('lesion_id') == lesion_id:
                    dimensions = lesion.get('dimensions_mm', [0, 0])
                    size = max(dimensions) if dimensions else 0
                    break
            
            # Check non-target lesions
            if np.isnan(size):
                for lesion in annotations.get('non_target_lesions', []):
                    if lesion.get('lesion_id') == lesion_id:
                        dimensions = lesion.get('dimensions_mm', [0, 0])
                        size = max(dimensions) if dimensions else 0
                        break
            
            lesion_series[lesion_id].append(size)
    
    # Get SLD and staging data
    sld_values = []
    stage_colors = []
    tnm_data = {'T': [], 'N': [], 'M': []}
    recist_responses = []
    new_lesion_flags = []
    
    seen_lesions = set()
    for i, study in enumerate(sorted_studies):
        annotations = study['annotations']
        
        # SLD
        sld = annotations.get('recist', {}).get('sum_mm', 0)
        sld_values.append(sld)
        
        # Staging
        staging = annotations.get('staging', {})
        stage_group = staging.get('stage_group', '')
        tnm_stage = staging.get('tnm_stage', '')
        stage_colors.append(get_stage_color(stage_group if stage_group != 'Unknown' else tnm_stage))
        
        # TNM components
        tnm_data['T'].append(staging.get('t_stage', 'TX'))
        tnm_data['N'].append(staging.get('n_stage', 'N0'))
        tnm_data['M'].append(staging.get('m_stage', 'M0'))
        
        # Check for new lesions
        current_lesions = set()
        
        # Add primary tumor if present
        if annotations.get('primary_tumor'):
            current_lesions.add('Primary_Tumor')
        
        # Add target and non-target lesions
        for lesion in annotations.get('target_lesions', []) + annotations.get('non_target_lesions', []):
            if lesion.get('lesion_id'):
                current_lesions.add(lesion['lesion_id'])
        
        new_lesion = i > 0 and len(current_lesions - seen_lesions) > 0
        new_lesion_flags.append(new_lesion)
        seen_lesions.update(current_lesions)
        
        # RECIST response
        response = determine_recist_response(sld, new_lesion, baseline_sld)
        recist_responses.append(response)
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[
            f'Patient {patient_id} — All Lesions, SLD (Stage-Colored), and TNM',
            'SLD with RECIST Response Labels',
            'TNM Staging'
        ],
        vertical_spacing=0.08,
        row_heights=[0.5, 0.3, 0.2]
    )
    
    # 1. Plot all lesions
    colors = px.colors.qualitative.Set3
    for i, (lesion_id, sizes) in enumerate(lesion_series.items()):
        if not sizes or all(np.isnan(sizes)):
            continue
        
        is_target = lesion_id in baseline_targets
        is_primary = lesion_id == 'Primary_Tumor'
        
        # Determine line style and appearance
        if is_primary:
            line_style = 'solid'
            line_width = 3
            alpha = 1.0
            marker_size = 8
            color = 'red'
        elif is_target:
            line_style = 'solid'
            line_width = 2
            alpha = 1.0
            marker_size = 6
            color = None  # Use default colors
        else:
            line_style = 'dash'
            line_width = 1.5
            alpha = 0.7
            marker_size = 6
            color = None  # Use default colors
        
        # Create display name
        if is_primary:
            display_name = f'Primary ({lesion_id})'
        else:
            display_name = f'{lesion_id}' + ('' if is_target else ' (NT)')
        
        # Create hover template
        if is_primary:
            hover_template = f'<b>{display_name}</b><br>' + \
                           'Date: %{x}<br>' + \
                           'Size: %{y} mm<br>' + \
                           'Type: Primary Tumor<br>' + \
                           '<extra></extra>'
        else:
            hover_template = f'<b>{lesion_id}</b><br>' + \
                           'Date: %{x}<br>' + \
                           'Size: %{y} mm<br>' + \
                           f'Type: {"Target" if is_target else "Non-target"}<br>' + \
                           '<extra></extra>'
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=sizes,
                mode='lines+markers',
                name=display_name,
                line=dict(dash=line_style, width=line_width, color=color),
                opacity=alpha,
                marker=dict(size=marker_size, color=color),
                hovertemplate=hover_template
            ),
            row=1, col=1
        )
    
    # 2. Plot SLD with stage-colored points and RECIST responses
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=sld_values,
            mode='lines+markers',
            name='SLD',
            line=dict(color='#444', width=2),
            marker=dict(size=8),
            hovertemplate='<b>SLD</b><br>' +
                         'Date: %{x}<br>' +
                         'Sum: %{y} mm<br>' +
                         '<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add stage-colored points
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=sld_values,
            mode='markers',
            name='Stage Points',
            marker=dict(
                size=12,
                color=stage_colors,
                line=dict(width=1, color='white')
            ),
            showlegend=False,
            hovertemplate='<b>SLD (Stage-Colored)</b><br>' +
                         'Date: %{x}<br>' +
                         'Sum: %{y} mm<br>' +
                         '<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add RECIST response labels
    for i, (date, sld, response) in enumerate(zip(dates, sld_values, recist_responses)):
        fig.add_annotation(
            x=date,
            y=sld + 10,
            text=response,
            showarrow=False,
            font=dict(size=10, color='white'),
            row=2, col=1
        )
    
    # Add new lesion indicators
    for i, (date, new_lesion) in enumerate(zip(dates, new_lesion_flags)):
        if new_lesion:
            fig.add_vrect(
                x0=date, x1=date,
                fillcolor="purple",
                opacity=0.1,
                layer="below",
                row=2, col=1
            )
    
    # 3. TNM staging strips
    tnm_colors = {'T': '#2A9D8F', 'N': '#E76F51', 'M': '#264653'}
    y_positions = {'T': 3, 'N': 2, 'M': 1}
    
    for component, values in tnm_data.items():
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[y_positions[component]] * len(dates),
                mode='markers+text',
                name=component,
                marker=dict(
                    size=20,
                    color=tnm_colors[component],
                    symbol='square'
                ),
                text=values,
                textposition='middle center',
                textfont=dict(color='white', size=10),
                showlegend=False,
                hovertemplate=f'<b>{component} Stage</b><br>' +
                             'Date: %{x}<br>' +
                             f'{component}: %{{text}}<br>' +
                             '<extra></extra>'
            ),
            row=3, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # Update axes
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Lesion Size (mm)", row=1, col=1)
    fig.update_yaxes(title_text="SLD (mm)", row=2, col=1)
    fig.update_yaxes(
        title_text="TNM",
        tickmode='array',
        tickvals=[1, 2, 3],
        ticktext=['M', 'N', 'T'],
        range=[0.5, 3.5],
        row=3, col=1
    )
    
    # Add stage color legend
    stage_colors_legend = {
        'I': 'green',
        'II': 'orange', 
        'III': 'red',
        'IV': 'purple'
    }
    
    for stage, color in stage_colors_legend.items():
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=10, color=color),
                name=f'Stage {stage}',
                showlegend=True
            )
        )
    
    return fig

# Main app
st.title("Radiology Report Dashboard")

# Load cohort labels data

cohort_labels_data = load_cohort_labels_data()
if cohort_labels_data:
    data = convert_cohort_labels_to_standard_format(cohort_labels_data)
    
    # Show data structure analysis in sidebar
    with st.sidebar.expander("📊 Data Structure"):
        validate_jsonl_structure(cohort_labels_data)
else:
    data = []

if not data:
    st.warning("No data loaded. Please check the cohort_labels.jsonl file.")
    st.stop()

# Show dataset statistics in sidebar
st.sidebar.subheader("Dataset Statistics")
total_patients = len(set(d['patient_id'] for d in data))
total_studies = len(data)
st.sidebar.metric("Total Patients", total_patients)
st.sidebar.metric("Total Studies", total_studies)

# Show tumor type (all cases are lung cancer)
st.sidebar.subheader("Tumor Type")
st.sidebar.text("• non-small cell lung carcinoma: All cases")

# Create patient list
patients = sorted(list(set(d['patient_id'] for d in data)))
selected_patient = st.selectbox("Select Patient", patients)

# Filter studies for selected patient
patient_studies = [d for d in data if d['patient_id'] == selected_patient]

# Show current analysis info as toast
st.toast(f"📊 Selected Patient: {selected_patient} | Studies: {len(patient_studies)}")

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📋 Individual Study", "📈 Timeline View", "🎯 Patient Course", "🔧 Raw Data"])

with tab1:
    st.header("Individual Study Analysis")
    
    study_ids = [s['study_id'] for s in patient_studies]
    selected_study = st.selectbox("Select Study", study_ids)
    
    # Display selected study data
    study_data = [d for d in data if d['study_id'] == selected_study][0]
    
    # Create columns for layout
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.header("Report Text")
        st.text_area("", study_data['report_text'], height=400)
    
    with col2:
        st.header("Study Details")
        
        # Display metadata as cards
        st.info(f"**Exam Date:** {study_data['exam_date']}")
        st.info(f"**Tumor Type:** {study_data['tumor_type']}")
        st.info(f"**Modality:** {study_data['modality']}")

with tab2:
    st.header("Study Timeline")
    
    # Create timeline view
    timeline_chart, timeline_df = create_timeline_view(patient_studies)
    
    if timeline_chart:
        st.plotly_chart(timeline_chart, use_container_width=True)
    
    # Timeline data table
    st.subheader("Timeline Data")
    st.dataframe(timeline_df, use_container_width=True)

with tab3:
    st.header("Comprehensive Patient Course Visualization")
    st.markdown("""
    This visualization shows the complete patient course including:
    - **All lesions** (target lesions as solid lines, non-target as dashed)
    - **SLD (Sum of Longest Diameters)** with stage-colored points
    - **RECIST response labels** (CR/PR/SD/PD)
    - **TNM staging** over time
    - **New lesion indicators** (purple vertical bars)
    """)
    
    # Create the comprehensive patient course visualization
    course_chart = create_patient_course_visualization(patient_studies, selected_patient)
    
    if course_chart:
        st.plotly_chart(course_chart, use_container_width=True)
        
        # Add summary information
        st.subheader("Patient Course Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Total studies
            st.metric("Total Studies", len(patient_studies))
        
        with col2:
            # Baseline SLD
            baseline_sld = patient_studies[0]['annotations'].get('recist', {}).get('sum_mm', 0)
            st.metric("Baseline SLD", f"{baseline_sld} mm")
        
        with col3:
            # Latest SLD
            latest_sld = patient_studies[-1]['annotations'].get('recist', {}).get('sum_mm', 0)
            st.metric("Latest SLD", f"{latest_sld} mm")
        
        with col4:
            # Best response
            responses = []
            baseline_sld = patient_studies[0]['annotations'].get('recist', {}).get('sum_mm', 0)
            seen_lesions = set()
            
            for i, study in enumerate(patient_studies):
                sld = study['annotations'].get('recist', {}).get('sum_mm', 0)
                
                # Check for new lesions
                current_lesions = set()
                for lesion in study['annotations'].get('target_lesions', []) + study['annotations'].get('non_target_lesions', []):
                    if lesion.get('lesion_id'):
                        current_lesions.add(lesion['lesion_id'])
                
                new_lesion = i > 0 and len(current_lesions - seen_lesions) > 0
                seen_lesions.update(current_lesions)
                
                response = determine_recist_response(sld, new_lesion, baseline_sld)
                responses.append(response)
            
            best_response = "SD"  # Default
            if "CR" in responses:
                best_response = "CR"
            elif "PR" in responses:
                best_response = "PR"
            elif "PD" in responses:
                best_response = "PD"
            
            st.metric("Best Response", best_response)
        
        # Detailed response timeline
        st.subheader("Response Timeline")
        response_data = []
        
        for i, study in enumerate(patient_studies):
            sld = study['annotations'].get('recist', {}).get('sum_mm', 0)
            staging = study['annotations'].get('staging', {})
            
            # Check for new lesions
            current_lesions = set()
            
            # Add primary tumor if present
            if study['annotations'].get('primary_tumor'):
                current_lesions.add('Primary_Tumor')
            
            # Add target and non-target lesions
            for lesion in study['annotations'].get('target_lesions', []) + study['annotations'].get('non_target_lesions', []):
                if lesion.get('lesion_id'):
                    current_lesions.add(lesion['lesion_id'])
            
            new_lesion = i > 0 and len(current_lesions - seen_lesions) > 0
            seen_lesions.update(current_lesions)
            
            response = determine_recist_response(sld, new_lesion, baseline_sld)
            
            response_data.append({
                'Study': study['study_id'],
                'Date': study['exam_date'],
                'SLD (mm)': sld,
                'TNM Stage': staging.get('tnm_stage', 'Unknown'),
                'RECIST Response': response,
                'New Lesions': 'Yes' if new_lesion else 'No'
            })
        
        response_df = pd.DataFrame(response_data)
        st.dataframe(response_df, use_container_width=True)
        
    else:
        st.warning("No data available for patient course visualization.")

with tab4:
    st.header("Raw JSONL Data")
    st.markdown("""
    This tab shows the raw JSONL data for debugging and inspection purposes.
    You can see the original structure of the data before conversion.
    """)
    
    # Show raw data for selected patient
    st.subheader(f"Raw Data for Patient {selected_patient}")
    
    # Filter raw data for selected patient
    raw_patient_data = [record for record in cohort_labels_data if record.get('patient_id') == selected_patient]
    
    if raw_patient_data:
        # Show each study's raw data
        for i, record in enumerate(raw_patient_data):
            with st.expander(f"Study {i+1} - {record.get('study_date', 'Unknown Date')}"):
                st.json(record)
                
                # Show report text if available
                if record.get('report_text'):
                    st.subheader("Report Text")
                    st.text_area("", record['report_text'], height=200, key=f"raw_report_{i}")
                else:
                    st.warning("No report text in this record")
    else:
        st.warning(f"No raw data found for patient {selected_patient}")
    
    # Show all available fields across all records
    st.subheader("All Available Fields in Dataset")
    if cohort_labels_data:
        all_fields = set()
        for record in cohort_labels_data:
            all_fields.update(record.keys())
        
        field_counts = {}
        for field in all_fields:
            count = sum(1 for record in cohort_labels_data if field in record)
            field_counts[field] = count
        
        # Create a dataframe to show field usage
        field_df = pd.DataFrame([
            {"Field": field, "Count": count, "Percentage": f"{count/len(cohort_labels_data)*100:.1f}%"}
            for field, count in sorted(field_counts.items())
        ])
        
        st.dataframe(field_df, use_container_width=True)
