#import <Cocoa/Cocoa.h>

@interface SBDelegate : NSObject <NSApplicationDelegate, NSMenuDelegate>
@property NSStatusItem *item;
@property NSMenu *menu;
@end

@implementation SBDelegate
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    self.item = [[NSStatusBar systemStatusBar] statusItemWithLength:NSSquareStatusItemLength];
    self.item.button.image = [NSImage imageWithSystemSymbolName:@"person.crop.circle.badge.clock" accessibilityDescription:@"SupportBot Presence"];
    self.menu = [NSMenu new]; self.menu.delegate = self; self.item.menu = self.menu;
    [self rebuildMenu];
}
- (NSString *)currentState {
    NSData *data = [NSData dataWithContentsOfURL:[NSURL URLWithString:@"http://127.0.0.1:47831/work-state"]];
    if (!data) return @"not_started";
    NSDictionary *value = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    return [value[@"state"] isKindOfClass:NSString.class] ? value[@"state"] : @"not_started";
}
- (NSMenuItem *)itemWithTitle:(NSString *)title state:(NSString *)state {
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:@selector(changeState:) keyEquivalent:@""];
    item.representedObject = state; item.target = self; return item;
}
- (void)rebuildMenu {
    NSString *state = [self currentState]; [self.menu removeAllItems];
    NSMenuItem *open = [[NSMenuItem alloc] initWithTitle:@"SupportBot Presence" action:@selector(openControl:) keyEquivalent:@""];
    open.target = self; [self.menu addItem:open]; [self.menu addItem:[NSMenuItem separatorItem]];
    NSSet *officialStateCodes = [NSSet setWithArray:@[@"vacation", @"sick_leave", @"business_trip", @"day_off"]];
    if (![state isEqualToString:@"working"] && ![officialStateCodes containsObject:state]) {
        NSString *title = ([state isEqualToString:@"not_started"] || [state isEqualToString:@"finished"]) ? @"Начать рабочий день" : @"Вернуться к работе";
        [self.menu addItem:[self itemWithTitle:title state:@"working"]];
    } else {
        NSMenuItem *leave = [[NSMenuItem alloc] initWithTitle:@"Покинуть рабочее место" action:nil keyEquivalent:@""];
        NSMenu *reasons = [NSMenu new];
        [reasons addItem:[self itemWithTitle:@"Обед" state:@"lunch"]];
        [reasons addItem:[self itemWithTitle:@"Перерыв" state:@"break"]];
        [reasons addItem:[self itemWithTitle:@"Совещание" state:@"meeting"]];
        [reasons addItem:[self itemWithTitle:@"Прочая причина" state:@"other"]];
        leave.submenu = reasons; [self.menu addItem:leave];
    }
    NSMenuItem *official = [[NSMenuItem alloc] initWithTitle:@"Официальное отсутствие" action:nil keyEquivalent:@""];
    NSMenu *officialStatuses = [NSMenu new];
    [officialStatuses addItem:[self itemWithTitle:@"Отпуск" state:@"vacation"]];
    [officialStatuses addItem:[self itemWithTitle:@"Больничный" state:@"sick_leave"]];
    [officialStatuses addItem:[self itemWithTitle:@"Командировка" state:@"business_trip"]];
    [officialStatuses addItem:[self itemWithTitle:@"Отгул" state:@"day_off"]];
    official.submenu = officialStatuses; [self.menu addItem:official];
    [self.menu addItem:[self itemWithTitle:@"Завершить рабочий день" state:@"finished"]];
}
- (void)menuWillOpen:(NSMenu *)menu { [self rebuildMenu]; }
- (void)openControl:(id)sender { [[NSWorkspace sharedWorkspace] openURL:[NSURL URLWithString:@"http://127.0.0.1:47831/control"]]; }
- (void)changeState:(NSMenuItem *)sender {
    NSString *reason = @"";
    NSString *startsAt = @""; NSString *endsAt = @"";
    if ([sender.representedObject isEqualToString:@"other"]) {
        NSAlert *alert = [NSAlert new]; alert.messageText = @"Прочая причина"; alert.informativeText = @"Опишите причину отсутствия на рабочем месте.";
        NSTextField *field = [[NSTextField alloc] initWithFrame:NSMakeRect(0, 0, 360, 28)]; field.placeholderString = @"Например: визит к врачу"; alert.accessoryView = field;
        [alert addButtonWithTitle:@"Подтверждаю"]; [alert addButtonWithTitle:@"Отмена"];
        if ([alert runModal] != NSAlertFirstButtonReturn) return;
        reason = [field.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if (reason.length == 0) { NSBeep(); return; }
    }
    NSSet *official = [NSSet setWithArray:@[@"vacation", @"sick_leave", @"business_trip", @"day_off"]];
    if ([official containsObject:sender.representedObject]) {
        NSAlert *alert = [NSAlert new]; alert.messageText = @"Период официального отсутствия"; alert.informativeText = @"Укажите дату и время начала и окончания.";
        NSView *view = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 380, 72)];
        NSDatePicker *start = [[NSDatePicker alloc] initWithFrame:NSMakeRect(0, 40, 380, 26)]; NSDatePicker *end = [[NSDatePicker alloc] initWithFrame:NSMakeRect(0, 4, 380, 26)];
        start.datePickerElements = NSYearMonthDayDatePickerElementFlag | NSHourMinuteDatePickerElementFlag; end.datePickerElements = start.datePickerElements;
        start.minDate = NSDate.date; start.dateValue = [NSDate.date dateByAddingTimeInterval:60]; end.minDate = start.dateValue; end.dateValue = [start.dateValue dateByAddingTimeInterval:28800];
        [view addSubview:start]; [view addSubview:end]; alert.accessoryView = view; [alert addButtonWithTitle:@"Подтверждаю"]; [alert addButtonWithTitle:@"Отмена"];
        if ([alert runModal] != NSAlertFirstButtonReturn) return;
        if ([end.dateValue compare:start.dateValue] != NSOrderedDescending) { NSBeep(); return; }
        NSDateFormatter *format = [NSDateFormatter new]; format.dateFormat = @"yyyy-MM-dd'T'HH:mm"; startsAt = [format stringFromDate:start.dateValue]; endsAt = [format stringFromDate:end.dateValue];
    }
    NSURL *url = [NSURL URLWithString:@"http://127.0.0.1:47831/work-state"];
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url]; request.HTTPMethod = @"POST"; [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    request.HTTPBody = [NSJSONSerialization dataWithJSONObject:@{@"state": sender.representedObject, @"reason": reason, @"starts_at": startsAt, @"ends_at": endsAt} options:0 error:nil];
    [[NSURLSession.sharedSession dataTaskWithRequest:request] resume];
}
@end

int main(void) { @autoreleasepool { NSApplication *app = NSApplication.sharedApplication; SBDelegate *delegate = [SBDelegate new]; app.delegate = delegate; [app setActivationPolicy:NSApplicationActivationPolicyAccessory]; [app run]; } return 0; }
