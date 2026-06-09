import type { PropsWithChildren, ReactNode } from "react";
import {
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View
} from "react-native";
import type { StyleProp, ViewStyle } from "react-native";

import { t, type SupportedLocale } from "./i18n";
import { colors, getSidebarThemes, radius, spacing, toneBackground, toneColor } from "./theme";
import type { MetricItem, ModuleRow, NavigationItem, ReadinessTone, SidebarTheme, SidebarThemeId } from "./types";

const companyLogoUri =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%231F3864'/%3E%3Cpath d='M18 18h18c7 0 11 4 11 9 0 4-2 7-6 8 5 1 8 5 8 10 0 6-5 10-13 10H18V18zm11 14h6c3 0 5-1 5-4s-2-4-5-4h-6v8zm0 17h7c4 0 6-2 6-5s-2-5-6-5h-7v10z' fill='white'/%3E%3C/svg%3E";

type TextProps = PropsWithChildren<{
  readonly muted?: boolean;
  readonly size?: "sm" | "md" | "lg" | "xl";
  readonly weight?: "regular" | "bold";
}>;

export function Label({ children, muted = false, size = "md", weight = "regular" }: TextProps) {
  return (
    <Text
      style={[
        styles.text,
        muted && styles.muted,
        size === "sm" && styles.textSm,
        size === "lg" && styles.textLg,
        size === "xl" && styles.textXl,
        weight === "bold" && styles.bold
      ]}
    >
      {children}
    </Text>
  );
}

export function Card({
  children,
  compact = false,
  style
}: PropsWithChildren<{ readonly compact?: boolean; readonly style?: StyleProp<ViewStyle> }>) {
  return <View style={[styles.card, compact && styles.cardCompact, style]}>{children}</View>;
}

export function Badge({ children, tone }: PropsWithChildren<{ readonly tone: ReadinessTone }>) {
  return (
    <View style={[styles.badge, { backgroundColor: toneBackground(tone) }]}>
      <Text style={[styles.badgeText, { color: toneColor(tone) }]}>{children}</Text>
    </View>
  );
}

type ButtonProps = PropsWithChildren<{
  readonly accessibilityLabel?: string;
  readonly onPress: () => void;
  readonly variant?: "primary" | "secondary" | "ghost";
}>;

export function ActionButton({ accessibilityLabel, children, onPress, variant = "primary" }: ButtonProps) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      hitSlop={4}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === "primary" && styles.buttonPrimary,
        variant === "secondary" && styles.buttonSecondary,
        variant === "ghost" && styles.buttonGhost,
        pressed && styles.buttonPressed
      ]}
    >
      <Text
        style={[
          styles.buttonText,
          variant === "primary" && styles.buttonTextPrimary,
          variant === "ghost" && styles.buttonTextGhost
        ]}
      >
        {children}
      </Text>
    </Pressable>
  );
}

type SectionHeaderProps = {
  readonly action?: ReactNode;
  readonly eyebrow?: string;
  readonly title: string;
  readonly description?: string;
};

export function SectionHeader({ action, description, eyebrow, title }: SectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionTitle}>
        {eyebrow ? <Label size="sm" muted>{eyebrow}</Label> : null}
        <Label size="lg" weight="bold">{title}</Label>
        {description ? <Label muted>{description}</Label> : null}
      </View>
      {action ? <View style={styles.sectionAction}>{action}</View> : null}
    </View>
  );
}

export function MetricGrid({ items }: { readonly items: readonly MetricItem[] }) {
  return (
    <View style={styles.metricGrid}>
      {items.map((item) => (
        <View key={item.id} style={[styles.metricCard, { borderLeftColor: toneColor(item.tone) }]}>
          <Label size="sm" muted>{item.label}</Label>
          <Text style={[styles.metricValue, { color: toneColor(item.tone) }]}>{item.value}</Text>
          <Label size="sm">{item.helper}</Label>
        </View>
      ))}
    </View>
  );
}

type FilterBarProps = {
  readonly active?: string;
  readonly filters: readonly string[];
  readonly onSelect?: (filter: string) => void;
};

export function FilterBar({ active, filters, onSelect }: FilterBarProps) {
  const selectedFilter = active ?? filters[0] ?? "";
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterBar}>
      {filters.map((filter) => {
        const selected = filter === selectedFilter;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected }}
            key={filter}
            onPress={() => onSelect?.(filter)}
            style={({ pressed }) => [styles.filterChip, selected && styles.filterChipActive, pressed && styles.buttonPressed]}
          >
            {selected ? <View style={styles.filterChipMark} /> : null}
            <Text style={[styles.filterText, selected && styles.filterTextActive]}>{filter}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function EmptyState({ description, title }: { readonly description: string; readonly title: string }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyMark}>-</Text>
      <Label weight="bold">{title}</Label>
      <Label size="sm" muted>{description}</Label>
    </View>
  );
}

type DataTableProps = {
  readonly onRowPress?: (row: ModuleRow) => void;
  readonly rows: readonly ModuleRow[];
  readonly selectedRowId?: string;
};

type LocalizedDataTableProps = DataTableProps & {
  readonly locale: SupportedLocale;
};

export function DataTable({ locale, onRowPress, rows, selectedRowId }: LocalizedDataTableProps) {
  const { width } = useWindowDimensions();
  const compact = width < 760;

  if (rows.length === 0) {
    return <EmptyState title={t(locale, "table.empty.title")} description={t(locale, "table.empty.description")} />;
  }

  if (compact) {
    return (
      <View style={styles.rowCards}>
        {rows.map((row) => (
          <Pressable
            accessibilityRole={onRowPress ? "button" : undefined}
            accessibilityState={selectedRowId === row.id ? { selected: true } : undefined}
            key={row.id}
            onPress={() => onRowPress?.(row)}
            style={({ pressed }) => [
              styles.rowCard,
              { borderLeftColor: toneColor(row.tone) },
              selectedRowId === row.id && styles.rowSelected,
              pressed && onRowPress && styles.buttonPressed
            ]}
          >
            <View style={styles.rowCardHeader}>
              <Label weight="bold">{row.category}</Label>
              <Badge tone={row.tone}>{row.status}</Badge>
            </View>
            <Label size="sm" muted>{t(locale, "table.mobile.owner", { owner: row.owner })}</Label>
            <Label size="sm">{row.nextStep}</Label>
          </Pressable>
        ))}
      </View>
    );
  }

  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={[styles.tableCell, styles.tableHeading]}>{t(locale, "table.columns.category")}</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>{t(locale, "table.columns.status")}</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>{t(locale, "table.columns.owner")}</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>{t(locale, "table.columns.nextStep")}</Text>
      </View>
      {rows.map((row) => (
        <Pressable
          accessibilityRole={onRowPress ? "button" : undefined}
          accessibilityState={selectedRowId === row.id ? { selected: true } : undefined}
          key={row.id}
          onPress={() => onRowPress?.(row)}
          style={({ pressed }) => [
            styles.tableRow,
            { borderLeftColor: toneColor(row.tone) },
            selectedRowId === row.id && styles.tableRowSelected,
            pressed && onRowPress && styles.buttonPressed
          ]}
        >
          <Text style={styles.tableCell}>{row.category}</Text>
          <View style={styles.tableCellShell}>
            <Badge tone={row.tone}>{row.status}</Badge>
          </View>
          <Text style={styles.tableCell}>{row.owner}</Text>
          <Text style={styles.tableCell}>{row.nextStep}</Text>
        </Pressable>
      ))}
    </View>
  );
}

type SidebarProps = {
  readonly compact: boolean;
  readonly items: readonly NavigationItem[];
  readonly activeId: NavigationItem["id"];
  readonly locale: SupportedLocale;
  readonly onSelect: (id: NavigationItem["id"]) => void;
  readonly onThemeChange: (id: SidebarThemeId) => void;
  readonly theme: SidebarTheme;
};

export function Sidebar({ activeId, compact, items, locale, onSelect, onThemeChange, theme }: SidebarProps) {
  const sidebarThemes = getSidebarThemes(locale);

  return (
    <View style={[styles.sidebar, { backgroundColor: theme.sidebar }, compact && styles.sidebarCompact]}>
      <View style={[styles.brandBlock, compact && styles.brandBlockCompact]}>
        <View style={styles.brandRow}>
          <Image accessibilityLabel={t(locale, "shell.companyLogo")} source={{ uri: companyLogoUri }} style={styles.logoImage} />
          <View>
            <Label size="lg" weight="bold">Bitween</Label>
            <Label size="sm" muted>{t(locale, "shell.brandSubtitle")}</Label>
          </View>
        </View>
      </View>
      <View style={[styles.themePanel, compact && styles.themePanelCompact]}>
        <Label size="sm" weight="bold">{t(locale, "shell.themePanel.title")}</Label>
        <View style={styles.themeChips}>
          {sidebarThemes.map((item) => {
            const selected = item.id === theme.id;
            return (
              <Pressable
                accessibilityHint={item.description}
                accessibilityLabel={t(locale, "shell.themePanel.optionLabel", { label: item.label, description: item.description })}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                key={item.id}
                onPress={() => onThemeChange(item.id)}
                style={({ pressed }) => [
                  styles.themeChip,
                  selected && { backgroundColor: theme.activeBackground, borderColor: theme.activeText },
                  pressed && styles.buttonPressed
                ]}
              >
                <View style={[styles.themeSwatch, { backgroundColor: item.swatchStart, borderColor: item.swatchEnd }]}>
                  <View style={[styles.themeSwatchInset, { backgroundColor: item.swatchEnd }]} />
                </View>
                <Text style={[styles.themeChipText, selected && { color: theme.activeText }]}>{item.label}</Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.themeCurrent}>
          <View style={[styles.themeCurrentRail, { backgroundColor: theme.activeText }]} />
          <View style={styles.themeCurrentCopy}>
            <Label size="sm" weight="bold">{t(locale, "shell.themePanel.current", { theme: theme.label })}</Label>
            <Label size="sm" muted>{theme.description}</Label>
          </View>
        </View>
      </View>
      <ScrollView
        horizontal={compact}
        showsHorizontalScrollIndicator={false}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={compact ? styles.navStrip : undefined}
      >
        {items.map((item) => {
          const active = item.id === activeId;
          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              key={item.id}
              onPress={() => onSelect(item.id)}
              style={[
                styles.navItem,
                compact && styles.navItemCompact,
                active && { backgroundColor: theme.activeBackground, borderLeftColor: item.accent }
              ]}
            >
              <Text style={[styles.navLabel, active && { color: theme.activeText }]}>{item.label}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

type ShellProps = PropsWithChildren<{
  readonly active: NavigationItem;
  readonly developerMode?: boolean;
  readonly employeeNumberLabel?: string;
  readonly items: readonly NavigationItem[];
  readonly locale: SupportedLocale;
  readonly logoutLabel: string;
  readonly modeLabel?: string;
  readonly onLogout?: () => void;
  readonly onSelect: (id: NavigationItem["id"]) => void;
  readonly onThemeChange: (id: SidebarThemeId) => void;
  readonly sessionLabel?: string;
  readonly sidebarTheme: SidebarTheme;
}>;

export function AppShell({
  active,
  children,
  developerMode = false,
  employeeNumberLabel,
  items,
  locale,
  logoutLabel,
  modeLabel,
  onLogout,
  onSelect,
  onThemeChange,
  sessionLabel,
  sidebarTheme
}: ShellProps) {
  const { width } = useWindowDimensions();
  const compact = width < 980;

  return (
    <View style={[styles.shell, compact && styles.shellCompact]}>
      <Sidebar
        activeId={active.id}
        compact={compact}
        items={items}
        locale={locale}
        onSelect={onSelect}
        onThemeChange={onThemeChange}
        theme={sidebarTheme}
      />
      <View style={styles.main}>
        <View style={[styles.header, compact && styles.headerCompact]}>
          <View style={styles.headerCopy}>
            <Label size="sm" muted>{active.eyebrow}</Label>
            <Label size="xl" weight="bold">{active.label}</Label>
            <Label muted>{active.description}</Label>
          </View>
          <View style={styles.headerActions}>
            {sessionLabel ? <Badge tone="neutral">{sessionLabel}</Badge> : null}
            {modeLabel ? <Badge tone={developerMode ? "attention" : "neutral"}>{modeLabel}</Badge> : null}
            {employeeNumberLabel ? <Badge tone="neutral">{employeeNumberLabel}</Badge> : null}
            {onLogout ? <ActionButton onPress={onLogout} variant="ghost">{logoutLabel}</ActionButton> : null}
          </View>
        </View>
        <ScrollView contentContainerStyle={[styles.content, compact && styles.contentCompact]} style={styles.contentScroll}>
          {children}
        </ScrollView>
        <View accessibilityLabel={t(locale, "shell.status.aria")} style={[styles.statusFooter, compact && styles.statusFooterCompact]}>
          <View style={styles.statusFooterGroup}>
            <View style={styles.statusDot} />
            <Label size="sm" weight="bold">{t(locale, "shell.status.previewTitle")}</Label>
            <Label size="sm" muted>{t(locale, "shell.status.demoCompany")}</Label>
          </View>
          <View style={styles.statusFooterGroup}>
            <Badge tone="ready">{t(locale, "shell.status.uiOnly")}</Badge>
            <Label size="sm" muted>{t(locale, "shell.status.logicUnchanged")}</Label>
          </View>
          <View style={styles.statusFooterGroup}>
            <Badge tone="neutral">{t(locale, "shell.status.strictTs")}</Badge>
            <Label size="sm" muted>{t(locale, "shell.status.reactNativeWebReady")}</Label>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "700"
  },
  bold: {
    fontWeight: "700"
  },
  brandBlock: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    marginBottom: spacing.lg,
    paddingBottom: spacing.lg
  },
  brandBlockCompact: {
    borderBottomWidth: 0,
    marginBottom: spacing.md,
    paddingBottom: 0
  },
  brandRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm
  },
  button: {
    alignItems: "center",
    borderRadius: radius.md,
    justifyContent: "center",
    minHeight: 42,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md
  },
  buttonGhost: {
    backgroundColor: "transparent"
  },
  buttonPrimary: {
    backgroundColor: colors.accent
  },
  buttonPressed: {
    opacity: 0.86
  },
  buttonSecondary: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.border,
    borderWidth: 1
  },
  buttonText: {
    color: colors.accent,
    flexShrink: 1,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center"
  },
  buttonTextGhost: {
    color: colors.muted
  },
  buttonTextPrimary: {
    color: colors.card
  },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    minWidth: 0,
    padding: spacing.lg
  },
  cardCompact: {
    padding: spacing.md
  },
  content: {
    gap: spacing.lg,
    minWidth: 0,
    padding: spacing.xl
  },
  contentCompact: {
    padding: spacing.md
  },
  contentScroll: {
    flex: 1,
    minWidth: 0
  },
  emptyMark: {
    color: colors.muted,
    fontSize: 28,
    fontWeight: "700",
    lineHeight: 32
  },
  emptyState: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderStyle: "dashed",
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.xl
  },
  filterBar: {
    gap: spacing.sm,
    paddingVertical: spacing.xs
  },
  filterChip: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  filterChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent
  },
  filterChipMark: {
    backgroundColor: colors.card,
    borderRadius: 999,
    height: 6,
    width: 6
  },
  filterText: {
    color: colors.muted,
    fontSize: 13,
    fontWeight: "700"
  },
  filterTextActive: {
    color: colors.card
  },
  header: {
    alignItems: "flex-start",
    backgroundColor: colors.card,
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: "row",
    gap: spacing.lg,
    justifyContent: "space-between",
    padding: spacing.xl
  },
  headerActions: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "flex-end"
  },
  headerCompact: {
    flexDirection: "column",
    padding: spacing.lg
  },
  headerCopy: {
    flex: 1,
    gap: spacing.xs,
    minWidth: 0
  },
  main: {
    backgroundColor: colors.bg,
    flex: 1,
    flexShrink: 1,
    minWidth: 0,
    overflow: "hidden"
  },
  logoImage: {
    borderRadius: radius.lg,
    height: 38,
    width: 38
  },
  metricCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderLeftWidth: 4,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 190,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  metricValue: {
    fontSize: 22,
    fontWeight: "800",
    lineHeight: 28
  },
  muted: {
    color: colors.muted
  },
  navItem: {
    borderLeftColor: "transparent",
    borderLeftWidth: 4,
    borderRadius: radius.md,
    gap: 2,
    marginBottom: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md
  },
  navItemCompact: {
    marginBottom: 0,
    minWidth: 128
  },
  navLabel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  navStrip: {
    gap: spacing.sm
  },
  rowCard: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderLeftWidth: 4,
    gap: spacing.sm,
    padding: spacing.md
  },
  rowCardHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    justifyContent: "space-between"
  },
  rowCards: {
    gap: spacing.md
  },
  rowSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
  },
  sectionAction: {
    alignItems: "flex-end"
  },
  sectionHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    justifyContent: "space-between"
  },
  sectionTitle: {
    flex: 1,
    gap: spacing.xs,
    minWidth: 0
  },
  shell: {
    backgroundColor: colors.bg,
    flex: 1,
    flexDirection: "row",
    minHeight: 720,
    overflow: "hidden"
  },
  shellCompact: {
    flexDirection: "column",
    minHeight: 0
  },
  sidebar: {
    backgroundColor: colors.sidebar,
    borderRightColor: colors.border,
    borderRightWidth: 1,
    flexBasis: 280,
    flexGrow: 0,
    flexShrink: 0,
    maxWidth: 280,
    minWidth: 280,
    overflow: "hidden",
    padding: spacing.lg,
    width: 280
  },
  sidebarCompact: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    borderRightWidth: 0,
    flexBasis: "auto",
    maxWidth: "100%",
    minWidth: 0,
    padding: spacing.md,
    width: "100%"
  },
  statusDot: {
    backgroundColor: colors.success,
    borderRadius: 999,
    height: 8,
    width: 8
  },
  statusFooter: {
    alignItems: "center",
    backgroundColor: colors.card,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    justifyContent: "space-between",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md
  },
  statusFooterCompact: {
    alignItems: "flex-start",
    paddingHorizontal: spacing.md
  },
  statusFooterGroup: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    minHeight: 30
  },
  themeChip: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
    minHeight: 34,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm
  },
  themeChips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  themeChipText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: "700",
    lineHeight: 16
  },
  themeCurrent: {
    alignItems: "stretch",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.sm
  },
  themeCurrentCopy: {
    flex: 1,
    gap: spacing.xs,
    minWidth: 0
  },
  themeCurrentRail: {
    borderRadius: 999,
    width: 4
  },
  themePanel: {
    backgroundColor: "rgba(255, 255, 255, 0.54)",
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    marginBottom: spacing.lg,
    padding: spacing.sm
  },
  themePanelCompact: {
    marginBottom: spacing.md
  },
  themeSwatch: {
    borderRadius: 999,
    borderWidth: 1,
    height: 18,
    overflow: "hidden",
    width: 18
  },
  themeSwatchInset: {
    alignSelf: "flex-end",
    height: 18,
    width: 9
  },
  table: {
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    minWidth: 0,
    overflow: "hidden"
  },
  tableCell: {
    color: colors.text,
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
    minWidth: 0
  },
  tableCellShell: {
    flex: 1,
    minWidth: 0
  },
  tableHeader: {
    backgroundColor: colors.accentSoft,
    flexDirection: "row",
    gap: spacing.md,
    minWidth: 0,
    padding: spacing.md
  },
  tableHeading: {
    color: colors.accent,
    fontWeight: "700"
  },
  tableRow: {
    alignItems: "center",
    borderTopColor: colors.divider,
    borderTopWidth: 1,
    borderLeftWidth: 4,
    flexDirection: "row",
    gap: spacing.md,
    minWidth: 0,
    padding: spacing.md
  },
  tableRowSelected: {
    backgroundColor: colors.accentSoft
  },
  text: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20
  },
  textLg: {
    fontSize: 18,
    lineHeight: 24
  },
  textSm: {
    fontSize: 12,
    lineHeight: 18
  },
  textXl: {
    fontSize: 24,
    lineHeight: 32
  }
});
