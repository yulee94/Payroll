import { Pressable, StyleSheet, Text } from 'react-native';
import { colors, spacing } from '../theme/tokens';

interface PrimaryButtonProps {
  label: string;
  onPress: () => void | Promise<void>;
  disabled?: boolean;
  tone?: 'primary' | 'danger' | 'success';
}

export function PrimaryButton({ label, onPress, disabled = false, tone = 'primary' }: PrimaryButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: colors[tone] },
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
      ]}
    >
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    borderRadius: 12,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  disabled: { opacity: 0.45 },
  pressed: { opacity: 0.8 },
  label: { color: '#fff', fontSize: 16, fontWeight: '800' },
});
