import type { PropsWithChildren } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { colors, spacing, toneColor } from "./theme";
import type { NavigationItem, ReadinessTone } from "./types";

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

export function Card({ children }: PropsWithChildren) {
  return <View style={styles.card}>{children}</View>;
}

export function Badge({ children, tone }: PropsWithChildren<{ readonly tone: ReadinessTone }>) {
  return (
    <View style={[styles.badge, { backgroundColor: `${toneColor(tone)}18` }]}>
      <Text style={[styles.badgeText, { color: toneColor(tone) }]}>{children}</Text>
    </View>
  );
}

type SidebarProps = {
  readonly items: readonly NavigationItem[];
  readonly activeId: NavigationItem["id"];
  readonly onSelect: (id: NavigationItem["id"]) => void;
};

export function Sidebar({ items, activeId, onSelect }: SidebarProps) {
  return (
    <View style={styles.sidebar}>
      <View style={styles.brandBlock}>
        <Label size="lg" weight="bold">Bitween</Label>
        <Label size="sm" muted>Business Platform</Label>
      </View>
      <ScrollView showsVerticalScrollIndicator={false}>
        {items.map((item) => {
          const active = item.id === activeId;
          return (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => onSelect(item.id)}
              style={[
                styles.navItem,
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
  return (
    <View style={styles.shell}>
      <Sidebar activeId={active.id} items={items} onSelect={onSelect} />
      <View style={styles.main}>
        <View style={styles.header}>
          <View>
            <Label size="sm" muted>{active.eyebrow}</Label>
            <Label size="xl" weight="bold">{active.label}</Label>
            <Label muted>{active.description}</Label>
          </View>
          <Badge tone="neutral">RN/TypeScript preview</Badge>
        </View>
        <ScrollView contentContainerStyle={styles.content}>{children}</ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    borderRadius: 6,
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
  card: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: 8,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg
  },
  content: {
    gap: spacing.lg,
    padding: spacing.xl
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
  main: {
    backgroundColor: colors.bg,
    flex: 1
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
    borderRadius: 6,
    gap: 2,
    marginBottom: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md
  },
  navLabel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  shell: {
    backgroundColor: colors.bg,
    flex: 1,
    flexDirection: "row",
    minHeight: 720
  },
  sidebar: {
    backgroundColor: colors.sidebar,
    borderRightColor: colors.border,
    borderRightWidth: 1,
    padding: spacing.lg,
    width: 280
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
