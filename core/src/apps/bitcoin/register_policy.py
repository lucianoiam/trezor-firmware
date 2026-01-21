from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Policy, PolicyRegistration

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def register_policy(
    msg: Policy, keychain: Keychain, coin: CoinInfo
) -> PolicyRegistration:
    from trezor import protobuf
    from trezor.crypto import hmac
    from trezor.messages import PolicyRegistration
    from trezor.ui.layouts import confirm_action
    from .parse_miniscript import parse_miniscript
    from .policy_rules import get_spending_rules

    miniscript = parse_miniscript(msg.template)
    xpub_tokens = [f"key {i+1}/{len(msg.xpubs)} (see next)" for i in range(len(msg.xpubs))]
    rules = get_spending_rules(miniscript, xpubs=xpub_tokens)

    for i, rule in enumerate(rules):
        await confirm_action(
            "/bitcoin/miniscript/register_policy",
            "Inheritance wallet setup",
            action=f'** Spend rule {i+1}/{len(rules)} **',
            description=rule,
        )

        await confirm_action(
            "/bitcoin/miniscript/register_policy",
            "Inheritance wallet setup",
            action=f'** Key {i+1}/{len(msg.xpubs)} **',
            description=msg.xpubs[i],
        )

    #await confirm_action(
    #    "/bitcoin/miniscript/register_policy",
    #    "Inheritance wallet setup",
    #    action=f"Review and register the wallet's policy: {msg.name}",
    #    extra_menu_items=[("Wallet descriptor", msg.template)],
    #)

    #await confirm_value(
    #    "Primary key",
    #    msg.xpubs[0],
    #    "Allows for spending available funds at any time.",
    #    "/bitcoin/miniscript/register_policy",
    #)

    #await confirm_value(
    #    "Inheritance key",
    #    msg.xpubs[1],
    #    f"Allows for spending available funds after {msg.blocks} blocks.",
    #    "/bitcoin/miniscript/register_policy",
    #)

    key = keychain.derive_slip21([b"SLIP-0019", b"Trezor-Policy"]).key()

    new_buffer = bytearray(protobuf.encoded_length(msg))
    protobuf.encode(new_buffer, msg)
    encoded_policy = bytes(new_buffer)
    policy_mac = hmac(hmac.SHA256, key, encoded_policy).digest()

    return PolicyRegistration(mac=policy_mac)
