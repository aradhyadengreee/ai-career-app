document.addEventListener('DOMContentLoaded', async function() {
    await loadResults();
});

async function loadResults() {
    try {
        console.log('Loading career recommendations...');
        
        const response = await fetch('/api/careers/recommendations');
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Results loaded successfully:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        displayProfileSummary(data.user_info, data.riasec_code);
        displayCareerRecommendations(data.recommendations);
        
    } catch (error) {
        console.error('Error loading results:', error);
        document.getElementById('careersList').innerHTML = `
            <div class="error-message">
                <h3>Error Loading Results</h3>
                <p>${error.message}</p>
                <p>Please complete your profile first.</p>
                <button class="btn-primary" onclick="window.location.href='/'">Go Back to Profile</button>
            </div>
        `;
    }
}


function displayProfileSummary(userInfo, riasecCode) {
    const container = document.getElementById('profileSummary');
    
    const profileHTML = `
        <div class="profile-card">
            <h3>Personal Information</h3>
            <div><strong>Name:</strong> ${userInfo.name}</div>
            <div><strong>Age:</strong> ${userInfo.age}</div>
            <div><strong>Occupation:</strong> ${userInfo.occupation.replace('_', ' ').toUpperCase()}</div>
            <div><strong>Education:</strong> ${userInfo.education_level}</div>
            ${userInfo.current_field ? `<div><strong>Field:</strong> ${userInfo.current_field}</div>` : ''}
            ${userInfo.experience_years > 0 ? `<div><strong>Experience:</strong> ${userInfo.experience_years} years</div>` : ''}
        </div>
        
        <div class="profile-card">
            <h3>RIASEC Profile</h3>
            <div class="riasec-code-large">${riasecCode}</div>
            <div class="riasec-scores">
                <div><strong>R:</strong> ${userInfo.realistic_score}/10</div>
                <div><strong>I:</strong> ${userInfo.investigative_score}/10</div>
                <div><strong>A:</strong> ${userInfo.artistic_score}/10</div>
                <div><strong>S:</strong> ${userInfo.social_score}/10</div>
                <div><strong>E:</strong> ${userInfo.enterprising_score}/10</div>
                <div><strong>C:</strong> ${userInfo.conventional_score}/10</div>
            </div>
        </div>
    `;
    
    container.innerHTML = profileHTML;
}

function displayCareerRecommendations(recommendations) {
    const container = document.getElementById('careersList');
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <h3>No career recommendations found</h3>
                <p>We couldn't find any careers matching your profile. Please try adjusting your preferences.</p>
            </div>
        `;
        return;
    }
    
    const recommendationsHTML = recommendations.map(career => `
        <div class="career-card">
            <div class="match-badge match-${Math.round(career.match_percentage/10)*10}">
                ${career.match_percentage}% Match
            </div>
            
            <h3>${career.family_title}</h3>
            <div class="career-subtitle">${career.nco_title}</div>
            <div class="nco-code">NCO: ${career.nco_code}</div>
            
            <div class="riasec-match">
                <strong>RIASEC Code:</strong> ${career.riasec_code}
            </div>
            
            <p class="job-description">${career.job_description || 'No description available'}</p>
            
            <div class="career-details-grid">
                <div class="detail-item">
                    <strong>Market Demand:</strong>
                    <div class="demand-score demand-${getDemandLevel(career.market_demand_score)}">
                        ${career.market_demand_score}/5
                    </div>
                </div>
                
                <div class="detail-item">
                    <strong>Automation Risk:</strong>
                    <span class="risk-${career.automation_risk.toLowerCase()}">${career.automation_risk}</span>
                </div>
                
                <div class="detail-item">
                    <strong>Industry Growth:</strong>
                    ${career.industry_growth || 'Not specified'}
                </div>
            </div>
            
            <div class="salary-section">
                <strong>Salary Range:</strong>
                <div class="salary-levels">
                    ${career.salary_range.entry ? `<div>Entry: ${career.salary_range.entry}</div>` : ''}
                    ${career.salary_range.mid ? `<div>Mid: ${career.salary_range.mid}</div>` : ''}
                    ${career.salary_range.senior ? `<div>Senior: ${career.salary_range.senior}</div>` : ''}
                </div>
            </div>
            
            ${career.primary_skills && career.primary_skills.length > 0 ? `
            <div class="skills-section">
                <strong>Primary Skills:</strong>
                <div class="skills-list">
                    ${career.primary_skills.map(skill => 
                        `<span class="skill-tag primary-skill">${skill}</span>`
                    ).join('')}
                </div>
            </div>
            ` : ''}
            
            ${career.emerging_skills && career.emerging_skills.length > 0 ? `
            <div class="skills-section">
                <strong>Emerging Skills:</strong>
                <div class="skills-list">
                    ${career.emerging_skills.map(skill => 
                        `<span class="skill-tag emerging-skill">${skill}</span>`
                    ).join('')}
                </div>
            </div>
            ` : ''}
            
            ${career.matching_parameters && career.matching_parameters.length > 0 ? `
            <div class="matching-parameters">
                <strong>Matching Parameters:</strong>
                <ul>
                    ${career.matching_parameters.map(param => `<li>${param}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
            
            ${career.learning_pathway ? `
            <div class="learning-pathway">
                <strong>Learning Pathway:</strong>
                <p>${career.learning_pathway}</p>
            </div>
            ` : ''}
            
            ${career.geographic_demand ? `
            <div class="geographic-demand">
                <strong>High Demand Locations:</strong>
                ${career.geographic_demand}
            </div>
            ` : ''}
        </div>
    `).join('');
    
    container.innerHTML = recommendationsHTML;
}

function getDemandLevel(score) {
    if (score >= 4) return 'high';
    if (score >= 3) return 'medium';
    return 'low';
}

function downloadResults() {
    const profileSummary = document.querySelector('.user-profile-summary').innerText;
    const careerCards = document.querySelectorAll('.career-card');
    
    let resultsText = "CAREER RECOMMENDATIONS REPORT\n";
    resultsText += "=".repeat(50) + "\n\n";
    resultsText += profileSummary + "\n\n";
    resultsText += "RECOMMENDED CAREERS:\n" + "=".repeat(30) + "\n\n";
    
    careerCards.forEach((card, index) => {
        const title = card.querySelector('h3').innerText;
        const match = card.querySelector('.match-badge').innerText;
        const description = card.querySelector('.job-description').innerText;
        
        resultsText += `${index + 1}. ${title} - ${match}\n`;
        resultsText += `   ${description}\n\n`;
    });
    
    const blob = new Blob([resultsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'career_recommendations.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert('Results downloaded as text file!');
}

async function logoutUser() {
    try {
        const response = await fetch('/api/user/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            alert('Logged out successfully');
            window.location.href = '/';
        } else {
            const errorData = await response.json();
            alert('Error logging out: ' + errorData.error);
        }
    } catch (error) {
        console.error('Error logging out:', error);
        alert('An error occurred while logging out');
    }
}