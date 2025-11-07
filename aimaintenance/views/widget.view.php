<?php declare(strict_types = 1);

/**
 * AI Maintenance widget view - Version with support for routine maintenance and tickets
 *
 * @var CView $this
 * @var array $data
 */

$chatHeight = $data['fields_values']['chat_height'] ?? 500;
$apiUrl = $data['fields_values']['api_url'] ?? 'http://localhost:5005';

// Get information about the current user
$userInfo = CWebUser::$data;
$userDisplay = '';
if (!empty($userInfo)) {
    $userDisplay = trim(($userInfo['name'] ?? '') . ' ' . ($userInfo['surname'] ?? ''));
    if (empty($userDisplay)) {
        $userDisplay = $userInfo['username'] ?? 'Unknown user';
    }
}

//Main container with better theme handling
$container = (new CDiv())
    ->addClass('ai-maintenance-widget')
    ->addStyle('height: 100%; overflow: hidden;')
    ->addItem(
        (new CDiv())
            ->addClass('ai-header')
            ->addItem(
                (new CDiv())
                    ->addClass('ai-header-content')
                    ->addItem((new CDiv())->addClass('ai-avatar')->addItem('🤖'))
                    ->addItem(
                        (new CDiv())
                            ->addClass('ai-header-text')
                            ->addItem((new CTag('h3', true, 'AI Maintenance Assistant')))
                            ->addItem((new CSpan('🐧 With support for routine maintenance'))->addClass('ai-status'))
                    )
                    ->addItem(
                        (new CDiv())
                            ->addClass('ai-header-actions')
                            ->addItem(
                                (new CButton('templates-btn', ''))
                                    ->setId('templates-btn')
                                    ->addClass('templates-button')
                                    ->setAttribute('title', 'View routine maintenance templates')
                                    ->addItem(
                                        (new CTag('svg'))
                                            ->setAttribute('viewBox', '0 0 24 24')
                                            ->setAttribute('width', '18')
                                            ->setAttribute('height', '18')
                                            ->setAttribute('fill', 'currentColor')
                                            ->addItem(
                                                (new CTag('path'))
                                                    ->setAttribute('d', 'M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z')
                                            )
                                    )
                            )
                    )
            )
    )
    ->addItem(
        (new CDiv())
            ->setId('ai-messages')
            ->addClass('ai-messages')
            ->addItem(
                (new CDiv())
                    ->addClass('ai-message system welcome-message')
                    ->addItem(
                        (new CDiv())
                            ->addClass('message-content')
                            ->addItem((new CDiv())->addClass('welcome-title')->addItem('🎯 Maintenance Assistant!'))
                            ->addItem((new CDiv())->addClass('welcome-subtitle')->addItem('Complete support for routine maintenance:'))
                            ->addItem(
                                (new CDiv())
                                    ->addClass('feature-grid')
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('🖥️'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Specific servers'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"srv-tuxito tomorrow 8-10am ticket 100-178306"'))
                                    )
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('👥'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Complete groups'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"Cloud group today 2-4pm with ticket 200-8341"'))
                                    )
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('🔄'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Daily maintenance'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"Daily backup at 2 AM ticket 500-43116"'))
                                    )
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('📅'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Weekly maintenance'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"Every Sunday from 1-3 AM with ticket 100-12345"'))
                                    )
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('🗓️'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Monthly maintenance'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"first day of each month ticket 200-67890"'))
                                    )
                                    ->addItem(
                                        (new CDiv())
                                            ->addClass('feature-card')
                                            ->addItem((new CDiv())->addClass('feature-icon')->addItem('🎫'))
                                            ->addItem((new CDiv())->addClass('feature-text')->addItem('Ticket management'))
                                            ->addItem((new CDiv())->addClass('feature-example')->addItem('"format: 100-178306, 200-8341"'))
                                    )
                            )
                            ->addItem(
                                (new CDiv())
                                    ->addClass('welcome-footer')
                                    ->addItem('💡 Click the 📋 button to see examples. Include ticket numbers for better tracking.')
                            )
                    )
            )
    )
    ->addItem(
        (new CDiv())
            ->addClass('ai-input-area')
            ->addItem(
                (new CDiv())
                    ->addClass('input-container')
                    ->addItem(
                        (new CTextArea('ai-input', ''))
                            ->setId('ai-input')
                            ->setAttribute('placeholder', _('💬 Describe the maintenance... E.g.: "srv-web01 tomorrow 8-10am ticket 100-178306", "daily backup 2 AM with ticket 200-8341""'))
                            ->setAttribute('rows', '3')
                    )
                    ->addItem(
                        (new CButton('ai-send-btn', ''))
                            ->setId('ai-send-btn')
                            ->addClass('send-button')
                            ->setAttribute('title', 'Send message (Enter to send)')
                            ->addItem(
                                (new CTag('svg'))
                                    ->setAttribute('viewBox', '0 0 24 24')
                                    ->setAttribute('width', '20')
                                    ->setAttribute('height', '20')
                                    ->setAttribute('fill', 'currentColor')
                                    ->addItem(
                                        (new CTag('path'))
                                            ->setAttribute('d', 'M2.01 21L23 12 2.01 3 2 10l15 2-15 2z')
                                    )
                            )
                    )
            )
    )
    ->addItem(
        (new CDiv())
            ->setId('ai-confirmation')
            ->addClass('ai-confirmation')
            ->addStyle('display: none;')
            ->addItem(
                (new CDiv())
                    ->addClass('confirmation-content')
                    ->addItem(new CTag('h4', true, _('✅ Confirm Maintenance')))
                    ->addItem(
                        (new CDiv())
                            ->setId('maintenance-details')
                            ->addClass('maintenance-details')
                    )
                    ->addItem(
                        (new CDiv())
                            ->addClass('confirmation-actions')
                            ->addItem(
                                (new CButton('confirm-maintenance', _('✅ Create Maintenance')))
                                    ->setId('confirm-maintenance')
                                    ->addClass('btn-alt btn-success')
                            )
                            ->addItem(
                                (new CButton('cancel-maintenance', _('❌ Cancel')))
                                    ->setId('cancel-maintenance')
                                    ->addClass('btn-alt btn-cancel')
                            )
                    )
            )
    )
    ->addItem(
        (new CDiv())
            ->setId('ai-loading')
            ->addClass('ai-loading')
            ->addStyle('display: none;')
            ->addItem((new CDiv())->addClass('loading-spinner'))
            ->addItem(new CSpan(_('⏳ Processing your request...')) )
    );

(new CWidgetView($data))
    ->addItem($container)
    ->setVar('api_url', $apiUrl)
    ->setVar('user_info', $userInfo)  // Add user information
    ->setVar('fields_values', $data['fields_values'])
    ->show();