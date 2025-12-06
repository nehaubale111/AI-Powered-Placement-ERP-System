// ========== UTILITY FUNCTIONS ==========

async function fetchData(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Fetch error for ${url}:`, error);
        throw error;
    }
}

function showSuccessAndReload(message) {
    alert(message);
    location.reload();
}

function confirmAction(message) {
    return confirm(message);
}

// ========== STUDENT DASHBOARD FUNCTIONS ==========

async function uploadResume(formId) {
    try {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        await fetchData("/upload_resume", { method: "POST", body: formData });
        showSuccessAndReload("Resume uploaded successfully!");
    } catch (error) {
        alert("Failed to upload resume: " + error.message);
    }
}

async function loadEvents() {
    try {
        const data = await fetchData("/student_events");
        const eventsList = document.querySelector(".events-list");

        let html = "";
        if (data.error) {
            html = `<li class="error">Error: ${data.error}</li>`;
        } else if (data.length === 0) {
            html = "<li>No upcoming events scheduled.</li>";
        } else {
            data.forEach(event => {
                const eventDate = new Date(event.date).toLocaleDateString();
                html += `
                    <li class="event-item">
                        <h4>${event.title}</h4>
                        <p>${event.description || 'No description available.'}</p>
                        <p><strong>Date:</strong> ${eventDate}</p>
                        <p><strong>Posted by:</strong> ${event.created_by_name || 'TPO'}</p>
                    </li>`;
            });
        }
        eventsList.innerHTML = html;
    } catch (error) {
        console.error('Error loading events:', error);
        document.querySelector(".events-list").innerHTML =
            '<li class="error">Failed to load events. Please try again.</li>';
    }
}

async function loadResources() {
    try {
        const data = await fetchData("/prep_resources_student");
        const resourceList = document.querySelector(".resource-list");

        let html = "";
        if (data.length === 0) {
            html = "<li>No resources available at the moment.</li>";
        } else {
            data.forEach(resource => {
                html += `
                    <li class="resource-item">
                        <h4>${resource.title || 'No title'}</h4>
                        <p>${resource.description || 'No description available'}</p>
                        <a href="/download_resource/${resource.file_path}" target="_blank">Download Resource</a>
                    </li>`;
            });
        }
        resourceList.innerHTML = html;
    } catch (error) {
        console.error('Error loading resources:', error);
        document.querySelector(".resource-list").innerHTML =
            '<li class="error">Failed to load resources. Please try again.</li>';
    }
}

// ========== RECRUITER DASHBOARD FUNCTIONS ==========

async function postJob(formId) {
    try {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        await fetchData("/post_job", { method: "POST", body: formData });
        showSuccessAndReload("Job posted successfully!");
    } catch (error) {
        alert("Failed to post job: " + error.message);
    }
}

async function updateStatus(appId, status) {
    try {
        await fetchData("/update_application", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `application_id=${appId}&status=${status}`
        });
        location.reload();
    } catch (error) {
        alert("Failed to update status: " + error.message);
    }
}

// ========== TPO DASHBOARD FUNCTIONS ==========

async function addStudent(formId) {
    try {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        await fetchData("/add_student", { method: "POST", body: formData });
        showSuccessAndReload("Student added successfully!");
    } catch (error) {
        alert("Failed to add student: " + error.message);
    }
}

async function postEvent(formId) {
    try {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        await fetchData("/add_event", { method: "POST", body: formData });
        showSuccessAndReload("Event posted successfully!");
    } catch (error) {
        alert("Failed to post event: " + error.message);
    }
}

async function postResource(formId) {
    try {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        await fetchData("/add_resource", { method: "POST", body: formData });
        showSuccessAndReload("Resource uploaded successfully!");
    } catch (error) {
        alert("Failed to upload resource: " + error.message);
    }
}

// ========== STUDENT MANAGEMENT ==========

/**
 * Delete student profile
 */
async function deleteStudent(studentId) {
    if (!confirmAction("Are you sure you want to delete this student and all their profile data?")) return;
    
    try {
        const response = await fetch(`/delete_student/${studentId}`, { 
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        alert(data.message);
        loadStudentProfiles(); // Reload the table
        
    } catch (error) {
        console.error("Error deleting student:", error);
        alert("Failed to delete student: " + error.message);
    }
}

/**
 * View student resume with better error handling
 */
function viewResume(resumePath) {
    if (resumePath && resumePath !== 'undefined' && resumePath !== 'null' && resumePath !== '') {
        window.open(`/download_resume/${resumePath}`, '_blank');
    } else {
        alert('No resume available for this student.');
    }
}

/**
 * Load and display student profiles
 */
async function loadStudentProfiles() {
    try {
        const data = await fetchData("/all_student_profiles");
        const tableBody = document.getElementById('studentTableBody');
        
        let html = "";
        if (data.length === 0) {
            html = `<tr>
                <td colspan="11" style="text-align: center; padding: 20px;">
                    No student records found in database.
                </td>
            </tr>`;
        } else {
            data.forEach(student => {
                html += `
                    <tr>
                        <td>${formatValue(student.student_id)}</td>
                        <td>${formatValue(student.first_name)} ${formatValue(student.last_name)}</td>
                        <td>${formatValue(student.roll_no)}</td>
                        <td>${formatValue(student.prn_no)}</td>
                        <td>${formatValue(student.email)}</td>
                        <td>${formatValue(student.phone)}</td>
                        <td>${formatValue(student.department)}</td>
                        <td>${formatValue(student.average)}%</td>
                        <td>${formatValue(student.live_backlogs)}</td>
                        <td>${student.resume_path ? '✅' : '❌'}</td>
                        <td>
                            <button onclick="viewFullProfile(${student.student_id})" class="view-btn">View</button>
                            <button onclick="viewResume('${student.resume_path || ''}')" class="view-btn">Resume</button>
                            <button onclick="deleteStudent(${student.student_id})" class="delete-btn">Delete</button>
                        </td>
                    </tr>`;
            });
        }
        tableBody.innerHTML = html;
    } catch (error) {
        console.error('Error loading student profiles:', error);
        document.getElementById('studentTableBody').innerHTML = 
            `<tr>
                <td colspan="11" style="text-align: center; padding: 20px; color: red;">
                    Error loading student records: ${error.message}
                </td>
            </tr>`;
    }
}

async function deleteResource(resourceId) {
    if (!confirmAction("Are you sure you want to delete this resource?")) return;
    try {
        const data = await fetchData(`/delete_resource/${resourceId}`, { method: "POST" });
        alert(data.message);
        location.reload();
    } catch (error) {
        console.error("Error deleting resource:", error);
        alert("Failed to delete resource: " + error.message);
    }
}

// ========== STUDENT PROFILE MANAGEMENT ==========

async function loadStudentProfiles() {
    try {
        const data = await fetchData("/all_student_profiles");
        const container = document.getElementById('studentCardsContainer');

        let html = "";
        if (data.length === 0) {
            html = `<div class="student-card-placeholder">No student profiles found.</div>`;
        } else {
            data.forEach(student => {
                html += createStudentCardHTML(student);
            });
        }
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading student profiles:', error);
        document.getElementById('studentCardsContainer').innerHTML =
            '<div class="student-card-placeholder">Failed to load student profiles.</div>';
    }
}

function createStudentCardHTML(student) {
    return `
        <div class="student-card ${student.edited_by_student ? 'edited-card' : ''}">
            <div class="student-card-header">
                <div class="student-name">
                    ${student.first_name || ''} ${student.last_name || ''}
                    ${student.edited_by_student ? '<span class="edited-tag">✎ Edited</span>' : ''}
                </div>
                <div class="student-id">PRN: ${student.prn_no || 'N/A'}</div>
            </div>
            
            ${createInfoSection('Basic Information', [
                { label: 'Roll No:', value: student.roll_no },
                { label: 'Gender:', value: student.gender },
                { label: 'DOB:', value: student.dob }
            ])}
            
            ${createInfoSection('Contact', [
                { label: 'Email:', value: student.email },
                { label: 'Phone:', value: student.phone },
                { 
                    label: 'Social:', 
                    value: createSocialLinks(student.linkedin_url, student.github_url),
                    isHTML: true
                }
            ])}
            
            ${createInfoSection('Academic', [
                { label: '10th:', value: student.tenth_percentage ? `${student.tenth_percentage}% (${student.tenth_year || ''})` : null },
                { label: '12th:', value: student.twelfth_percentage ? `${student.twelfth_percentage}% (${student.twelfth_year || ''})` : null },
                { label: 'Diploma:', value: student.diploma_percentage ? `${student.diploma_percentage}%` : null }
            ])}
            
            ${createInfoSection('Engineering', [
                { label: 'Department:', value: student.department },
                { label: 'Passing Year:', value: student.engg_passing_year },
                { label: 'Average:', value: student.average ? `${student.average}%` : null },
                { label: 'Backlogs:', value: student.live_backlogs || '0' }
            ])}
            
            <div class="card-actions">
                <button onclick="viewFullProfile(${student.student_id})" class="card-btn view">Full View</button>
                <button onclick="viewResume('${student.resume_path}')" class="card-btn resume">Resume</button>
                <button onclick="deleteStudent(${student.student_id})" class="card-btn delete">Delete</button>
            </div>
        </div>`;
}

function createInfoSection(title, items) {
    const rows = items.map(item => {
        const value = item.isHTML ? item.value : (item.value || '<span class="empty-data">Not provided</span>');
        return `
            <div class="info-row">
                <div class="info-label">${item.label}</div>
                <div class="info-value">${value}</div>
            </div>`;
    }).join('');

    return `
        <div class="info-section">
            <div class="section-title">${title}</div>
            ${rows}
        </div>`;
}

function createSocialLinks(linkedinUrl, githubUrl) {
    return `
        <div class="social-links">
            ${linkedinUrl ? `<a href="${linkedinUrl}" target="_blank">LinkedIn</a>` : '<span class="empty-data">LinkedIn</span>'}
            ${githubUrl ? `<a href="${githubUrl}" target="_blank">GitHub</a>` : '<span class="empty-data">GitHub</span>'}
        </div>`;
}

// ========== ANNOUNCEMENTS CAROUSEL ==========

function initAnnouncementsCarousel() {
    const slide = document.querySelector('.carousel-slide');
    if (!slide) return;

    const announcements = slide.querySelectorAll('p');
    if (announcements.length <= 3) return;

    let index = 0;
    const visibleCount = 3;

    setInterval(() => {
        index++;
        if (index > announcements.length - visibleCount) {
            index = 0;
        }
        const height = announcements[0].offsetHeight;
        slide.style.transform = `translateY(-${index * height}px)`;
    }, 3000);
}

// ========== INITIALIZATION ==========

function initializeDashboard() {
    loadResources();
    loadApplications();
    loadEvents();
    loadJobs();
    loadStudentProfiles();
    initAnnouncementsCarousel();
}

document.addEventListener('DOMContentLoaded', initializeDashboard);
let currentExportType = '';
let selectedColumns = [];

function openColumnModal(exportType) {
    currentExportType = exportType;
    document.getElementById('columnModal').style.display = 'block';
    
    // Set default selections
    const defaultColumns = ['student_id', 'first_name', 'last_name', 'department', 'average', 'email'];
    document.querySelectorAll('input[name="export_columns"]').forEach(checkbox => {
        checkbox.checked = defaultColumns.includes(checkbox.value);
    });
}

function closeColumnModal() {
    document.getElementById('columnModal').style.display = 'none';
    currentExportType = '';
}

function selectAllColumns() {
    document.querySelectorAll('input[name="export_columns"]').forEach(checkbox => {
        checkbox.checked = true;
    });
}

function deselectAllColumns() {
    document.querySelectorAll('input[name="export_columns"]').forEach(checkbox => {
        checkbox.checked = false;
    });
}

function proceedWithSelectedColumns() {
    selectedColumns = Array.from(document.querySelectorAll('input[name="export_columns"]:checked'))
        .map(checkbox => checkbox.value);
    
    if (selectedColumns.length === 0) {
        alert('Please select at least one column to export.');
        return;
    }
    
    closeColumnModal();
    
    if (currentExportType === 'excel') {
        exportCustomExcel();
    } else if (currentExportType === 'pdf') {
        exportCustomPDF();
    }
}

function exportCustomExcel() {
    if (studentData.length === 0) {
        alert('No data available to export');
        return;
    }

    try {
        const columnMapping = {
            'student_id': 'Student ID',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'roll_no': 'Roll No',
            'prn_no': 'PRN No',
            'dob': 'Date of Birth',
            'gender': 'Gender',
            'phone': 'Phone',
            'email': 'Email',
            'department': 'Department',
            'average': 'Average %',
            'live_backlogs': 'Live Backlogs',
            'tenth_percentage': '10th %',
            'tenth_year': '10th Year',
            'twelfth_percentage': '12th %',
            'twelfth_year': '12th Year',
            'programming_languages': 'Programming Languages',
            'academic_projects': 'Academic Projects',
            'certificates': 'Certificates',
            'resume_path': 'Resume Available'
        };

        const excelData = studentData.map(student => {
            const row = {};
            selectedColumns.forEach(col => {
                const displayName = columnMapping[col] || col;
                if (col === 'resume_path') {
                    row[displayName] = student[col] ? 'Yes' : 'No';
                } else {
                    row[displayName] = student[col] || '';
                }
            });
            return row;
        });

        const ws = XLSX.utils.json_to_sheet(excelData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Selected Student Data');
        
        const currentDate = new Date().toISOString().split('T')[0];
        XLSX.writeFile(wb, `student_selected_data_${currentDate}.xlsx`);
        
    } catch (error) {
        console.error('Error exporting custom Excel:', error);
        alert('Error exporting to Excel: ' + error.message);
    }
}

function exportCustomPDF() {
    if (studentData.length === 0) {
        alert('No data available to export');
        return;
    }

    try {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        const columnMapping = {
            'student_id': 'ID',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'roll_no': 'Roll No',
            'prn_no': 'PRN No',
            'email': 'Email',
            'department': 'Department',
            'average': 'Avg %',
            'live_backlogs': 'Backlogs',
            'tenth_percentage': '10th %',
            'twelfth_percentage': '12th %',
            'programming_languages': 'Programming',
            'resume_path': 'Resume'
        };

        const tableHeaders = selectedColumns.map(col => columnMapping[col] || col);
        const tableData = studentData.map(student => 
            selectedColumns.map(col => {
                if (col === 'resume_path') {
                    return student[col] ? 'Yes' : 'No';
                }
                return truncateText(student[col] || '', 20);
            })
        );

        doc.text(`Custom Student Data - ${new Date().toISOString().split('T')[0]}`, 14, 15);
        
        doc.autoTable({
            head: [tableHeaders],
            body: tableData,
            startY: 20,
            styles: { fontSize: 8 },
            headStyles: { fillColor: [0, 170, 255] }
        });

        doc.save(`student_custom_data_${new Date().toISOString().split('T')[0]}.pdf`);
        
    } catch (error) {
        console.error('Error exporting custom PDF:', error);
        alert('Error exporting to PDF: ' + error.message);
    }
}