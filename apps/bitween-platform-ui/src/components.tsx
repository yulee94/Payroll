import type { PropsWithChildren, ReactNode } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View
} from "react-native";
import type { StyleProp, ViewStyle } from "react-native";

import { colors, radius, spacing, toneBackground, toneColor } from "./theme";
import type { MetricItem, ModuleRow, NavigationItem, ReadinessTone } from "./types";

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
  readonly onPress: () => void;
  readonly variant?: "primary" | "secondary" | "ghost";
}>;

export function ActionButton({ children, onPress, variant = "primary" }: ButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={[
        styles.button,
        variant === "primary" && styles.buttonPrimary,
        variant === "secondary" && styles.buttonSecondary,
        variant === "ghost" && styles.buttonGhost
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

export function FilterBar({ active = 0, filters }: { readonly active?: number; readonly filters: readonly string[] }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterBar}>
      {filters.map((filter, index) => {
        const selected = index === active;
        return (
          <View key={filter} style={[styles.filterChip, selected && styles.filterChipActive]}>
            <Text style={[styles.filterText, selected && styles.filterTextActive]}>{filter}</Text>
          </View>
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

export function DataTable({ rows }: { readonly rows: readonly ModuleRow[] }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;

  if (rows.length === 0) {
    return <EmptyState title="표시할 항목이 없습니다." description="연동 데이터가 생기면 목록이 자동으로 채워집니다." />;
  }

  if (compact) {
    return (
      <View style={styles.rowCards}>
        {rows.map((row) => (
          <View key={row.id} style={styles.rowCard}>
            <View style={styles.rowCardHeader}>
              <Label weight="bold">{row.category}</Label>
              <Badge tone={row.tone}>{row.status}</Badge>
            </View>
            <Label size="sm" muted>담당: {row.owner}</Label>
            <Label size="sm">{row.nextStep}</Label>
          </View>
        ))}
      </View>
    );
  }

  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={[styles.tableCell, styles.tableHeading]}>구분</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>상태</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>담당</Text>
        <Text style={[styles.tableCell, styles.tableHeading]}>다음 작업</Text>
      </View>
      {rows.map((row) => (
        <View key={row.id} style={styles.tableRow}>
          <Text style={styles.tableCell}>{row.category}</Text>
          <View style={styles.tableCellShell}>
            <Badge tone={row.tone}>{row.status}</Badge>
          </View>
          <Text style={styles.tableCell}>{row.owner}</Text>
          <Text style={styles.tableCell}>{row.nextStep}</Text>
        </View>
      ))}
    </View>
  );
}

type SidebarProps = {
  readonly compact: boolean;
  readonly items: readonly NavigationItem[];
  readonly activeId: NavigationItem["id"];
  readonly onSelect: (id: NavigationItem["id"]) => void;
};

export function Sidebar({ activeId, compact, items, onSelect }: SidebarProps) {
  return (
    <View style={[styles.sidebar, compact && styles.sidebarCompact]}>
      <View style={[styles.brandBlock, compact && styles.brandBlockCompact]}>
        <Label size="lg" weight="bold">Bitween</Label>
        <Label size="sm" muted>Business Platform</Label>
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
              key={item.id}
              onPress={() => onSelect(item.id)}
              style={[
                styles.navItem,
                compact && styles.navItemCompact,
                active && { backgroundColor: `${item.accent}18`, borderLeftColor: item.accent }
              ]}
            >
              <Text style={[styles.navEyebrow, active && { color: item.accent }]}>{item.eyebrow}</Text>
              <Text style={[styles.navLabel, active && { color: item.accent }]}>{item.label}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

type ShellProps = PropsWithChildren<{
  readonly active: NavigationItem;
  readonly items: readonly NavigationItem[];
  readonly onSelect: (id: NavigationItem["id"]) => void;
}>;

export function AppShell({ active, children, items, onSelect }: ShellProps) {
  const { width } = useWindowDimensions();
  const compact = width < 980;

  return (
    <View style={[styles.shell, compact && styles.shellCompact]}>
      <Sidebar activeId={active.id} compact={compact} items={items} onSelect={onSelect} />
      <View style={styles.main}>
        <View style={[styles.header, compact && styles.headerCompact]}>
          <View style={styles.headerCopy}>
            <Label size="sm" muted>{active.eyebrow}</Label>
            <Label size="xl" weight="bold">{active.label}</Label>
            <Label muted>{active.description}</Label>
          </View>
          <Badge tone="neutral">RN/TypeScript preview</Badge>
        </View>
        <ScrollView contentContainerStyle={[styles.content, compact && styles.contentCompact]}>{children}</ScrollView>
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
  buttonSecondary: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.border,
    borderWidth: 1
  },
  buttonText: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: "700"
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
    padding: spacing.lg
  },
  cardCompact: {
    padding: spacing.md
  },
  content: {
    gap: spacing.lg,
    padding: spacing.xl
  },
  contentCompact: {
    padding: spacing.md
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
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  filterChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent
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
    flex: 1
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
  navEyebrow: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "700"
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
    minHeight: 720
  },
  shellCompact: {
    flexDirection: "column",
    minHeight: 0
  },
  sidebar: {
    backgroundColor: colors.sidebar,
    borderRightColor: colors.border,
    borderRightWidth: 1,
    padding: spacing.lg,
    width: 280
  },
  sidebarCompact: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    borderRightWidth: 0,
    padding: spacing.md,
    width: "100%"
  },
  table: {
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
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
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
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
