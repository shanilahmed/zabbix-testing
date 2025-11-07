class WidgetAIMaintenance extends CWidget {
    
    onInitialize() {
        super.onInitialize();
        this.api_url = '';
        this.current_parsed_data = null;
        this.user_info = null;
        this.templates = null;
        this.request_timeout = 60000; // 60 Seconds
        this.retry_count = 0;
        this.max_retries = 2;
    }

    processUpdateResponse(response) {
        this.api_url = response.fields_values?.api_url || 'http://localhost:5005';
        
        // Process user information correctly
        if (response.user_info) {
            this.user_info = {
                username: response.user_info.username || '',
                name: response.user_info.name || '',
                surname: response.user_info.surname || '',
                userid: response.user_info.userid || ''
            };
        }
        
        super.processUpdateResponse(response);
    }

    setContents(response) {
        super.setContents(response);
        this.setupEventListeners();
        this.loadMaintenanceTemplates();
        this.checkBackendConnection();
    }

    async checkBackendConnection() {
        try {
            const response = await fetch(`${this.api_url}/health`, {
                method: 'GET',
                timeout: 10000
            });
            
            if (!response.ok) {
                throw new Error(`Backend unavailable (${response.status})`);
            }
            
            const data = await response.json();
            
            if (data.status === 'unhealthy' || data.status === 'degraded') {
                this.addMessage(
                    `System reports status: ${data.status}\n` +
                    `Zabbix status: ${data.zabbix_connected ? 'Connected' : 'Disconnected'}\n` +
                    `AI Provider: ${data.ai_provider || 'Not available'}\n` +
                    `Bitmask support: ${data.features?.includes('bitmask_support') ? 'Enabled' : 'Disabled'}\n` +
                    `${data.status === 'degraded' ? 'Some features may be limited.' : ''}`,
                    'warning'
                );
            } else {
                // Display information about available functions
                const features = data.features || [];
                this.addMessage(
                    `Connected System - v${data.version}\n` + 
                    `Zabbix: ${data.zabbix_connected ? 'Connected' : 'Disconnected'}\n` + 
                    `AI: ${data.ai_provider}\n` + 
                    `Features: ${features.includes('routine_maintenance') ? 'Routines': ''} ` + 
                    `${features.includes('bitmask_support') ? 'Bitmask' : ''} ` + 
                    `${features.includes('ticket_support') ? 'Tickets' : ''}`, 
                    'success'
                );
            }
            
        } catch (error) {
            `Connected System - v${data.version}\n` + 
            `Zabbix: ${data.zabbix_connected ? 'Connected' : 'Disconnected'}\n` + 
            `AI: ${data.ai_provider}\n` + 
            `Features: ${features.includes('routine_maintenance') ? 'Routines': ''} ` + 
            `${features.includes('bitmask_support') ? 'Bitmask' : ''} ` + 
            `${features.includes('ticket_support') ? 'Tickets' : ''}`, 
            'success'
        }
    }

    setupEventListeners() {
        const send_btn = this._body.querySelector('#ai-send-btn');
        const input = this._body.querySelector('#ai-input');
        const confirm_btn = this._body.querySelector('#confirm-maintenance');
        const cancel_btn = this._body.querySelector('#cancel-maintenance');
        const templates_btn = this._body.querySelector('#templates-btn');

        if (send_btn) {
            send_btn.addEventListener('click', () => this.onSendMessage());
        }
        
        if (input) {
            input.addEventListener('keypress', (e) => this.onKeyPress(e));
            input.addEventListener('input', (e) => this.adjustTextareaHeight(e.target));
            input.addEventListener('focus', this.clearPlaceholderOnce.bind(this));
        }
        
        if (confirm_btn) {
            confirm_btn.addEventListener('click', () => this.onConfirmMaintenance());
        }
        
        if (cancel_btn) {
            cancel_btn.addEventListener('click', () => this.onCancelMaintenance());
        }
        
        if (templates_btn) {
            templates_btn.addEventListener('click', () => this.showTemplates());
        }
    }

    clearPlaceholderOnce(event) {
        const input = event.target;
        if (input.value === '' && input.placeholder.includes('Ex.:')) {
            input.placeholder = 'Describe the maintenance you need...';
        }
        input.removeEventListener('focus', this.clearPlaceholderOnce);
    }

    adjustTextareaHeight(textarea) {
        if (!textarea) return;
        
        textarea.style.height = 'auto';
        const maxHeight = 300;
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = newHeight + 'px';
    }

    onKeyPress(event) {
        if (event.key === 'Enter') {
            if (event.ctrlKey || event.metaKey) {
                event.preventDefault();
                const input = event.target;
                const start = input.selectionStart;
                const end = input.selectionEnd;
                input.value = input.value.substring(0, start) + '\n' + input.value.substring(end);
                input.selectionStart = input.selectionEnd = start + 1;
                this.adjustTextareaHeight(input);
            } else {
                event.preventDefault();
                this.onSendMessage();
            }
        }
    }

    async loadMaintenanceTemplates() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const response = await fetch(`${this.api_url}/maintenance/templates`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (response.ok) {
                const templates = await response.json();
                this.templates = templates.templates;
                console.log("Loaded templates:", Object.keys(this.templates || {}).length);
            } else {
                console.warn(`Error loading templates: ${response.status}`);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn("Timeout loading templates");
            } else {
                console.error("Error loading templates:", error);
            }
        }
    }

    showTemplates() {
        if (!this.templates) {
            this.addMessage(
                "Templates are not available at this time.\n\n" +
                "**Routine maintenance examples:**\n" +
                "• **Daily:** 'Daily backup at 2 AM with ticket 100-178306'\n" +
                "• **Weekly:** 'Maintenance Sundays from 1-3 AM ticket 200-8341'\n" +
                "• **Monthly specific day:** 'Cleaning on the 5th of each month with ticket 500-43116'\n" +
                "• **Monthly weekday:** 'Update the first Sunday of each month ticket 600-78901'",
                'info'
            );
            return;
        }
        
        let templateMsg = "**Routine Maintenance Templates**\n\n";
        
        Object.entries(this.templates).forEach(([type, info]) => {
            const icon = type === 'daily' ? 'Daily' : type === 'weekly' ? 'Weekly' : 'Monthly';
            templateMsg += `${icon} **${info.name}**\n`;
            templateMsg += `${info.description}\n`;
            templateMsg += "**Examples:**\n";
            info.examples.forEach(example => {
                templateMsg += `• "${example}"\n`;
            });
            templateMsg += "\n";
        });
        
        templateMsg += "**Routine Maintenance Tips:**\n";
        templateMsg += "• **Daily:** 'every day', 'every day', 'daily'\n";
        templateMsg += "• **Weekly:** 'every Monday', 'every Sunday', 'weekly'\n";
        templateMsg += "• **Monthly (day):** '5th of each month', '15th of the day', '1st of the month'\n";
        templateMsg += "• **Monthly (week):** 'first Sunday', 'second week', 'last Friday'\n";
        templateMsg += "• **Tickets:** Always include numbers like '100-178306', '200-8341'\n";
        templateMsg += "\n**Tip:** Routine maintenance uses internal bitmasks for accurate scheduling.";
        
        this.addMessage(templateMsg, 'info');
    }

    async onSendMessage() {
        const input = this._body.querySelector('#ai-input');
        if (!input) return;
        
        const message = input.value.trim();
        if (!message) {
            this.highlightInput(input);
            return;
        }

        // Length validation
        if (message.length < 5) {
            this.addMessage("The message is very short. Describe what type of maintenance you need to create.", 'warning');
            this.highlightInput(input);
            return;
        }

        if (message.length > 1000) {
            this.addMessage("The message is too long. Please be more concise.", 'warning');
            return;
        }

        // Add "thinking" animation to the avatar
        const avatar = this._body.querySelector('.ai-avatar');
        if (avatar) {
            avatar.classList.add('thinking');
        }

        //Clear input and display user message
        input.value = '';
        input.style.height = 'auto';
        this.addMessage(message, 'user');
        this.showLoading(true, 'Analyzing request...');

        try {
            const requestData = { 
                message: message,
                user_info: this.user_info
            };

            const response = await this.makeRequest('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Server error (${response.status})`);
            }

            const data = await response.json();
            this.handleInteractiveResponse(data);
            this.retry_count = 0;

        } catch (error) {
            console.error("Error in onSendMessage:", error);
            this.handleRequestError(error, message);
        } finally {
            this.showLoading(false);
            if (avatar) {
                avatar.classList.remove('thinking');
            }
        }
    }

    async makeRequest(endpoint, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.request_timeout);

        try {
            const response = await fetch(`${this.api_url}${endpoint}`, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('The request took too long. Please try again..');
            }
            throw error;
        }
    }

    highlightInput(input) {
        if (!input) return;
        
        input.style.borderColor = '#ff4757';
        input.focus();
        
        setTimeout(() => {
            input.style.borderColor = '';
        }, 2000);
    }

    handleRequestError(error, originalMessage) {
        if (this.retry_count < this.max_retries && 
            (error.message.includes('timeout') || error.message.includes('network'))) {
            
            this.retry_count++;
            this.addMessage(
                `Connection error (attempt ${this.retry_count}/${this.max_retries + 1}). Retrying...`,
                'warning'
            );
            
            setTimeout(() => {
                const input = this._body.querySelector('#ai-input');
                if (input) {
                    input.value = originalMessage;
                    this.onSendMessage();
                }
            }, 2000);
        } else {
            this.retry_count = 0;
            const errorMessage = error.message.includes('fetch') 
                ? "Could not connect to the backend. Verify that the service is running."
                : `Error: ${error.message}`;
            
            this.addMessage(`${errorMessage}`, 'error');
        }
    }

    handleInteractiveResponse(data) {
        if (!data || typeof data !== 'object') {
            this.addMessage("Invalid server response", 'error');
            return;
        }

        const responseType = data.type;
        
        switch (responseType) {
            case 'maintenance_request':
                this.current_parsed_data = data;
                this.showMaintenanceResults(data);
                break;
                
            case 'help_request':
                this.addMessage(data.message, 'assistant');
                if (data.examples) {
                    this.showExamples(data.examples);
                }
                break;
                
            case 'off_topic':
                this.addMessage(data.message, 'info');
                break;
                
            case 'clarification_needed':
                this.addMessage(data.message, 'warning');
                if (data.detected_info && Object.keys(data.detected_info).length > 0) {
                    this.showDetectedInfo(data.detected_info);
                }
                break;
                
            case 'error':
                this.addMessage(data.message, 'error');
                break;
                
            default:
                console.warn(`Unknown response type: ${responseType}`);
                this.addMessage(
                    data.message || 'I received a response that I could not fully process.', 
                    'assistant'
                );
                break;
        }
    }

    showDetectedInfo(detectedInfo) {
        let infoMsg = "\n**Information detected:**\n";
        Object.entries(detectedInfo).forEach(([key, value]) => {
            if (value) {
                const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                infoMsg += `• ${displayKey}: ${value}\n`;
            }
        });
        this.addMessage(infoMsg, 'info');
    }

    showMaintenanceResults(data) {
        if (!data) return;

        let message = '';
        
        if (data.message && data.message.trim()) {
            message = data.message + '\n\n';
        } else {
            message = `**Analysis completed**\n\n`;
        }
        
        // Show ticket information if present
        if (data.ticket_number && data.ticket_number.trim()) {
            message += `**Ticket:** ${data.ticket_number}\n\n`;
        }
        
        // Show maintenance type
        const recurrenceLabel = this.getRecurrenceTypeLabel(data.recurrence_type);
        const isRoutine = data.recurrence_type !== 'once';
        
        const typeIcon = isRoutine ? 'Routine' : 'Single';
        message += `**Type:** ${recurrenceLabel} (${typeIcon})\n\n`;
        
        // Recurrence settings if applicable
        if (isRoutine && data.recurrence_config) {
            const configInfo = this.formatRecurrenceConfig(data.recurrence_type, data.recurrence_config);
            if (configInfo) {
                message += `**Configuration:** ${configInfo}\n\n`;
            }
        }
        
        //Show search summary if available
        if (data.search_summary) {
            const summary = data.search_summary;
            message += `**Summary:**\n`;
            message += `• Hosts Found: ${summary.total_hosts_found}\n`;
            message += `• Groups Found: ${summary.total_groups_found}\n`;
            if (summary.hosts_by_tags > 0) {
                message += `• Hosts by tags: ${summary.hosts_by_tags}\n`;
            }
            if (summary.has_ticket) {
                message += `• With ticket: Yes\n`;
            }
            if (summary.is_routine) {
                message += `• Routine maintenance: Yes\n`;
            }
            message += '\n';
        }
        
        //Show found resources
        message = this.appendResourcesInfo(message, data);
        
        // Show schedule
        if (data.start_time && data.end_time) {
            message += `**Period:**\n`;
            message += `• From: ${data.start_time}\n`;
            message += `• Until: ${data.end_time}\n\n`;
        }
        
        if (data.description && data.description.trim()) {
            message += `**Description:** ${data.description}\n\n`;
        }

        if (data.confidence && data.confidence > 0) {
            message += `**Trust:** ${data.confidence}%`;
        }

        this.addMessage(message, 'assistant');

        // Show confirmation if there are valid resources
        const hasValidTargets = this.hasValidTargets(data);
        
        if (hasValidTargets) {
            this.showConfirmation(data);
        } else {
            this.addMessage('No valid hosts or groups were found to create maintenance', 'warning');
        }
    }
    
    appendResourcesInfo(baseMessage, data) {
        let message = baseMessage;

        // Hosts found
        if (data.found_hosts && data.found_hosts.length > 0) {
            message += `**Servers found (${data.found_hosts.length}):**\n`;
            data.found_hosts.forEach(host => {
                const displayName = host.name || host.host;
                message += `• ${displayName} (${host.host})\n`;
            });
            message += '\n';
        }

        // Groups found
        if (data.found_groups && data.found_groups.length > 0) {
            message += `**Groups found (${data.found_groups.length}):**\n`;
            data.found_groups.forEach(group => {
                message += `• ${group.name}\n`;
            });
            message += '\n';
        }

        // Tags by triggers
        if (data.trigger_tags && data.trigger_tags.length > 0) {
            message += `**Tags by triggers:**\n`;
            data.trigger_tags.forEach(tag => {
                message += `• ${tag.tag}: ${tag.value}\n`;
            });
            message += '\n';
        }

        // Resources not found
        if (data.missing_hosts && data.missing_hosts.length > 0) {
            message += `**Servers NOT found:**\n`;
            data.missing_hosts.forEach(host => {
                message += `• ${host}\n`;
            });
            message += '\n';
        }

        if (data.missing_groups && data.missing_groups.length > 0) {
            message += `**Groups NOT found:**\n`;
            data.missing_groups.forEach(group => {
                message += `• ${group}\n`;
            });
            message += '\n';
        }

        return message;
    }

    hasValidTargets(data) {
        return (data.found_hosts && data.found_hosts.length > 0) || 
               (data.found_groups && data.found_groups.length > 0);
    }

    showExamples(examples) {
        if (!examples || examples.length === 0) return;
        
        let exampleMsg = "\n**Examples:**\n\n";
        
        examples.forEach((example, index) => {
            exampleMsg += `${index + 1}. **${example.title}**\n`;
            exampleMsg += `   "${example.example}"\n\n`;
        });
        
        this.addMessage(exampleMsg, 'info');
    }

    async onConfirmMaintenance() {
        if (!this.current_parsed_data) {
            this.addMessage("No maintenance data to confirm", 'error');
            return;
        }
        
        // Verify that there are at least hosts or groups
        const hasValidTargets = this.hasValidTargets(this.current_parsed_data);
        
        if (!hasValidTargets) {
            this.addMessage('There are no valid hosts or groups to create maintenance', 'error');
            return;
        }
        
        this.showLoading(true, 'Creating maintenance...');
        
        try {
            // Prepare data for sending
            const maintenanceData = {
                start_time: this.current_parsed_data.start_time,
                end_time: this.current_parsed_data.end_time,
                description: this.current_parsed_data.description || '',
                trigger_tags: this.current_parsed_data.trigger_tags || [],
                recurrence_type: this.current_parsed_data.recurrence_type || 'once',
                ticket_number: this.current_parsed_data.ticket_number || '',
                user_info: this.user_info
            };

            // Add recurrence configuration if it exists
            if (this.current_parsed_data.recurrence_config) {
                maintenanceData.recurrence_config = this.current_parsed_data.recurrence_config;
            }

            // Add hosts if they exist
            if (this.current_parsed_data.found_hosts && this.current_parsed_data.found_hosts.length > 0) {
                maintenanceData.hosts = this.current_parsed_data.found_hosts.map(h => h.host);
            }

            // Add groups if they exist
            if (this.current_parsed_data.found_groups && this.current_parsed_data.found_groups.length > 0) {
                maintenanceData.groups = this.current_parsed_data.found_groups.map(g => g.name);
            }

            console.log("Maintenance data to be sent:", maintenanceData);

            const response = await this.makeRequest('/create_maintenance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(maintenanceData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Server error (${response.status})`);
            }

            const data = await response.json();            
            
            this.addMessage(data.message, 'success');
            
            // Display additional information for routine maintenance
            if (data.is_routine) {
                this.addMessage(
                    `**Routine Maintenance Configured**\n` +
                    `• Type: ${data.recurrence_type}\n` +
                    `• ID: ${data.maintenance_id || 'Automatically generated'}\n` +
                    `• Will run automatically based on configuration\n` +
                    `• Uses internal bitmasks for precise scheduling`,
                    'info'
                );
            }
            
            // Update maintenance list
            this.updateMaintenanceList();

        } catch (error) {
            console.error("Error creating maintenance:", error);
            this.addMessage(
                `Error creating maintenance: ${error.message}`,
                'error'
            );
        } finally {
            this.showLoading(false);
            this.onCancelMaintenance();
        }
    }

    async updateMaintenanceList() {
        try {
            const response = await this.makeRequest('/maintenance/list');
            
            if (!response.ok) {
                console.warn(`Error getting maintenance list: ${response.status}`);
                return;
            }

            const data = await response.json();
            console.log("Maintenance updates:", data.maintenances?.length || 0);
            
            // Display maintenance statistics
            const maintenances = data.maintenances || [];
            if (maintenances.length > 0) {
                const routineCount = maintenances.filter(m => m.is_routine).length;
                const oneTimeCount = maintenances.length - routineCount;
                const withTickets = maintenances.filter(m => m.ticket_number).length;
                
                // Count by types of routines
                const dailyCount = maintenances.filter(m => m.routine_type === 'daily').length;
                const weeklyCount = maintenances.filter(m => m.routine_type === 'weekly').length;
                const monthlyCount = maintenances.filter(m => m.routine_type === 'monthly').length;
                
                this.addMessage(
                    `**Maintenance Summary:**\n` +
                    `• One-Time: ${oneTimeCount}\n` +
                    `• Routine: ${routineCount}\n` +
                    ` - Daily: ${dailyCount}\n` +
                    ` - Weekly: ${weeklyCount}\n` +
                    ` - Monthly: ${monthlyCount}\n` +
                    `• With Tickets: ${withTickets}\n` +
                    `• Total: ${maintenances.length}`,
                    'info'
                );
            }
        } catch (error) {
            console.error("Error actualizando lista:", error);
        }
    }

    addMessage(message, type) {
        if (!message) return;

        const messages = this._body.querySelector('#ai-messages');
        if (!messages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Preserve line breaks and basic markdown formatting
        let formattedMessage = this.escapeHtml(message).replace(/\n/g, '<br>');
        
        // Convert bold text **text** to <strong>
        formattedMessage = formattedMessage.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Highlight tickets in the text
        formattedMessage = formattedMessage.replace(
            /\b(\d{3}-\d{3,6})\b/g,
            '<span class="ticket-highlight">$1</span>'
        );
        
        contentDiv.innerHTML = formattedMessage;
        
        messageDiv.appendChild(contentDiv);
        messages.appendChild(messageDiv);
        
        // Scroll soft at the end
        this.scrollToBottom(messages);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToBottom(element) {
        if (!element) return;
        
        // Use requestAnimationFrame for better performance
        requestAnimationFrame(() => {
            element.scrollTop = element.scrollHeight;
        });
    }

    showLoading(show, message = 'Processing...') {
        const loading = this._body.querySelector('#ai-loading');
        if (!loading) return;

        if (show) {
            const loadingText = loading.querySelector('span');
            if (loadingText) {
                loadingText.textContent = message;
            }
            loading.style.display = 'flex';
        } else {
            loading.style.display = 'none';
        }
    }

    getRecurrenceTypeLabel(type) {
        const labels = {
            'once': 'Unique',
            'daily': 'Daily',
            'weekly': 'Weekly',
            'monthly': 'Monthly'
        };
        return labels[type] || type;
    }
    
    formatRecurrenceConfig(type, config) {
        if (!config || typeof config !== 'object') return '';
        
        let info = '';
        
        switch (type) {
            case 'daily':
                info = `Each ${config.every || 1} day(s)`;
                if (config.start_time !== undefined) {
                    const hours = Math.floor(config.start_time / 3600);
                    const minutes = Math.floor((config.start_time % 3600) / 60);
                    info += `at ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
                }
                break;
                
            case 'weekly': {                
                const dayNames = this.decodeDaysBitmask(config.dayofweek || 1);
                info = `Each ${config.every || 1} week(s) the ${dayNames.join(', ')}`;
                if (config.start_time !== undefined) {
                    const hours = Math.floor(config.start_time / 3600);
                    const minutes = Math.floor((config.start_time % 3600) / 60);
                    info += ` at ${hours.toString().padStart(2,'0')}:${minutes.toString().padStart(2,'0')}`;
                }
                break;
            }
                
            case 'monthly':
                if (config.day !== undefined) {
                    info = `The day ${config.day} decade ${config.every || 1} month(s)`;
                } else if (config.dayofweek !== undefined) {
                    const dayNames = this.decodeDaysBitmask(config.dayofweek);
                    const weekNames = {1: 'first', 2: 'second', 3: 'third', 4: 'quarter', 5: 'last'};
                    const weekName = weekNames[config.every] || 'first';
                    info = `${weekName} week - ${dayNames.join(', ')} of each month`;
                }
                
                if (config.start_time !== undefined) {
                    const hours = Math.floor(config.start_time / 3600);
                    const minutes = Math.floor((config.start_time % 3600) / 60);
                    info += ` at ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
                }
                break;
                
            default:
                info = 'Custom settings';
        }
        
        return info;
    }
    
    decodeDaysBitmask(bitmask) {
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const result = [];
        
        for (let i = 0; i < 7; i++) {
            if (bitmask & (1 << i)) {
                result.push(days[i]);
            }
        }
        
        return result.length > 0 ? result : ['Lunes'];
    }
    
    decodeMonthsBitmask(bitmask) {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
        const result = [];
        
        for (let i = 0; i < 12; i++) {
            if (bitmask & (1 << i)) {
                result.push(months[i]);
            }
        }
        
        return result.length > 0 ? result : ['Every month'];
    }

    showConfirmation(data) {
        const confirmation = this._body.querySelector('#ai-confirmation');
        const details = this._body.querySelector('#maintenance-details');
        
        if (!confirmation || !details) {
            console.error("Confirmation elements not found");
            return;
        }

        const isRoutine = data.recurrence_type !== 'once';
        const recurrenceLabel = this.getRecurrenceTypeLabel(data.recurrence_type);
        const hasTicket = data.ticket_number && data.ticket_number.trim();

        let detailsHtml = '<h5>Maintenance Details:</h5><ul>';

        // Show ticket if present
        if (hasTicket) {
            detailsHtml += `<li><strong>Ticket:</strong> ${this.escapeHtml(data.ticket_number)}</li>`;
        }

        // Type of maintenance
        detailsHtml += `<li><strong>Type:</strong> ${recurrenceLabel}${isRoutine ? ' (Routine)' : ''}</li>`;

        // Recurrence settings if applicable
        if (isRoutine && data.recurrence_config) {
            const configInfo = this.formatRecurrenceConfig(data.recurrence_type, data.recurrence_config);
            if (configInfo) {
                detailsHtml += `<li><strong>Recurrence:</strong> ${this.escapeHtml(configInfo)}</li>`;
            }
            
            // Show technical details for routines
            detailsHtml += `<li><strong>Technical configuration:</strong> `;
            if (data.recurrence_type === 'weekly') {
                detailsHtml += `Bitmask Days: ${data.recurrence_config.dayofweek || 1}`;
            } else if (data.recurrence_type === 'monthly') {
                if (data.recurrence_config.day !== undefined) {
                    detailsHtml += `Day ${data.recurrence_config.day} of the month`;
                } else if (data.recurrence_config.dayofweek !== undefined) {
                    detailsHtml += `Bitmask Days: ${data.recurrence_config.dayofweek}, Week: ${data.recurrence_config.every || 1}`;
                }
                
                // Show month bitmask if present
                if (data.recurrence_config.month !== undefined && data.recurrence_config.month !== 4095) {
                    const monthNames = this.decodeMonthsBitmask(data.recurrence_config.month);
                    detailsHtml += `, Months: ${monthNames.join(', ')} (bitmask: ${data.recurrence_config.month})`;
                }
            } else if (data.recurrence_type === 'daily') {
                detailsHtml += `Each ${data.recurrence_config.every || 1} day(s)`;
            }
            detailsHtml += `</li>`;
        }

        // Show servers if there are any
        if (data.found_hosts && data.found_hosts.length > 0) {
            const hostNames = data.found_hosts.map(h => h.name || h.host).join(', ');
            detailsHtml += `<li><strong>Servers (${data.found_hosts.length}):</strong> ${this.escapeHtml(hostNames)}</li>`;
        }

        // Show groups if any
        if (data.found_groups && data.found_groups.length > 0) {
            const groupNames = data.found_groups.map(g => g.name).join(', ');
            detailsHtml += `<li><strong>Groups (${data.found_groups.length}):</strong> ${this.escapeHtml(groupNames)}</li>`;
        }

        // Show trigger tags if any
        if (data.trigger_tags && data.trigger_tags.length > 0) {
            const tagStrings = data.trigger_tags.map(t => `${t.tag}: ${t.value}`).join(', ');
            detailsHtml += `<li><strong>Tags by triggers:</strong> ${this.escapeHtml(tagStrings)}</li>`;
        }

        detailsHtml += `<li><strong>Period:</strong> ${this.escapeHtml(data.start_time)} - ${this.escapeHtml(data.end_time)}</li>`;
        
        // Display name to be generated
        const previewName = this.generateMaintenanceName(data);
        detailsHtml += `<li><strong>Name:</strong> ${this.escapeHtml(previewName)}</li>`;
        
        detailsHtml += '</ul>';

        // Warning for routine maintenance
        if (isRoutine) {
            detailsHtml += '<div class="routine-warning">';
            detailsHtml += '<strong>Routine Maintenance:</strong><br>';
            detailsHtml += 'This maintenance will repeat automatically based on the specified settings.';
            detailsHtml += 'Uses internal bitmasks for accurate scheduling in Zabbix.';
            detailsHtml += 'Please carefully review the schedules and frequency before confirming.';
            detailsHtml += '</div>';
        }

        // Warning if there is no ticket
        if (!hasTicket) {
            detailsHtml += '<div class="no-ticket-warning">';
            detailsHtml += '<strong>No Ticket:</strong><br>';
            detailsHtml += 'The standard name will be used. To include a ticket in future requests,';
            detailsHtml += 'mention it in the message (e.g., "ticket 100-178306").';
            detailsHtml += '</div>';
        }

        details.innerHTML = detailsHtml;
        confirmation.style.display = 'flex';
        
        // Focus the first button for accessibility
        const confirmButton = confirmation.querySelector('#confirm-maintenance');
        if (confirmButton) {
            setTimeout(() => confirmButton.focus(), 100);
        }
    }

    generateMaintenanceName(data) {
        /**
        * Generates the maintenance name to display in the preview
        * Replicates the backend logic
        */
        if (!data) return "AI Maintenance: No data";
        
        const ticket_number = data.ticket_number && data.ticket_number.trim();
        const recurrence_type = data.recurrence_type || 'once';
        
        // Base prefix according to type of maintenance
        let base_prefix;
        if (recurrence_type === 'once') {
            base_prefix = 'AI Maintenance';
        } else {
            base_prefix = 'AI Routine Maintenance';
        }
        
        //If there is a ticket, use it as the main name
        if (ticket_number) {
            return `${base_prefix}: ${ticket_number}`;
        }
        
        // If there is no ticket, use the current system (resource names)
        const maintenance_name_parts = [];
        
        if (data.found_hosts && data.found_hosts.length > 0) {
            const hostNames = data.found_hosts.map(h => h.name || h.host).slice(0, 3);
            maintenance_name_parts.push(...hostNames);
            if (data.found_hosts.length > 3) {
                maintenance_name_parts.push(`y ${data.found_hosts.length - 3} hosts more`);
            }
        }
        
        if (data.found_groups && data.found_groups.length > 0) {
            const groupNames = data.found_groups.map(g => `Group ${g.name}`).slice(0, 2);
            maintenance_name_parts.push(...groupNames);
            if (data.found_groups.length > 2) {
                maintenance_name_parts.push(`y ${data.found_groups.length - 2} more groups`);
            }
        }
        
        if (maintenance_name_parts.length > 0) {
            return `${base_prefix}: ${maintenance_name_parts.join(', ')}`;
        } else {
            return `${base_prefix}: Various resources`;
        }
    }

    onCancelMaintenance() {
        const confirmation = this._body.querySelector('#ai-confirmation');
        if (confirmation) {
            confirmation.style.display = 'none';
        }
        this.current_parsed_data = null;
        
        //  Focus back on input...
        const input = this._body.querySelector('#ai-input');
        if (input) {
            setTimeout(() => input.focus(), 100);
        }
    }

    // Method to clean up resources when the widget is destroyed
    destroy() {
        //Cancel any pending requests
        if (this.currentRequest) {
            this.currentRequest.abort();
        }
        
        // Clean timeouts
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
        }
        
        super.destroy?.();
    }
}
