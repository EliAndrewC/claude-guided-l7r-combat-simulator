L7R Combat Simulator
--------------------

# Requirements
* Python 3.8 or better
* pyyaml module (run `pip install pyyaml` to get it)


# Installing

You can run the L7R combat simulator by cloning the l7r git repository,
checking out the "new-simulator" branch, and running it on the command line.


# Running

Open a command prompt, change directories to the l7r directory from your
clone of the git repo, and run:
`python -m simulation -h`

This will explain your command line arguments. The simplest way to run is:
`python -m simulation -i path-to-characters -t number-of-trials`
where "path-to-characters" is the name of a directory where you've saved
character and group files, and "number-of-trials" is the number of trials
you want to run for a simulation.

If you include the argument `--log-level info` then you will get an event
log in a file called "simulation.log" in your working directory. You may
do `--log-level debug` instead for more verbose output, but the extra
information is unlikely to be interesting unless you're investigating bugs.


# Input: Character and Group Files

You can create characters and assign them to groups by writing YAML format
files.

Character files may have any name. The groups file must be called "groups.yaml".
An input directory may have any number of character files, but it must have one
and only one groups file.


## Groups File (groups.yaml)

The groups file must be named "groups.yaml". It defines two groups, indicates
which group is the control group and which group is the test group, and defines
the characters in each group.

A groups file looks like this:

```
east:
  control: true
  characters:
  - Akodo
  - Doji
west:
  test: true
  characters:
  - Bayushi
  - Hida
```

The `characters` section of a group should list the names of the characters in
the group. The names must be the same names that appear in the character files.


## Character Files

Character files may use any filename and any file extension.

A character file must have the sections:
* name
* rings
* skills

It may have either a school, or a profession, or neither.

It may also have the optional sections:
* xp
* advantages
* disadvantages
* strategies

Characters with peasant professions should also have the optional section:
* abilities

An example character file looks like this:
```
name: Taro
xp: 9001
rings:
  air: 2
  earth: 3
  fire: 4
  water: 3
  void: 3
skills:
  attack: 4
  parry: 5
advantages:
- strength of the earth
- great destiny
disadvantages:
- contrary
- long temper
- meddler
- proud
- short temper
- transparent
- vain
strategies:
  action: AlwaysAttackActionStrategy
  parry: NeverParryStrategy
```

A peasant character file looks like this:
```
name: Kikuchiyo
xp: 9001
rings:
  air: 2
  earth: 3
  fire: 4
  water: 3
  void: 3
skills:
  attack: 4
  parry: 3
abilities:
  crippled bonus: 2
  damage bonus: 1
  failed parry damage bonus: 2
  initiative bonus: 2
  missed attack bonus: 1
  rolled damage bonus: 1
advantages:
 - fierce
 - great destiny
 - lucky
 - quick healer
disadvantages:
 - contrary
 - dark secret
 - emotional
 - poor
 - proud
 - short temper
 - thoughtless
 - transparent
 - unkempt
```

### Character Name

The character name defines the character's name. It must match the name
in the groups file.

If the name field is omitted, the character will be assigned a random UUID
as its name. Since you have to name the character in the groups file, a
random name isn't going to work out, so make sure to provide a name!


### Character XP

The xp field defines the number of Experience Points used to build the character.

If omitted, the character will be given 100 XP.

The XP field is enforced, so if you don't want to calculate how many XP it takes
to build your character, it is recommended to specify a very large number such as
9001.


### Character School, Profession, or Neither

You may put a "school" or "profession", or neither.


#### Characters with Samurai Schools

Characters with a samurai school receive many benefits:
* School ring raised to 3 for free
* Attack and Parry start at 1 for free
* School knacks start at 1 for free

The following schools are available:
* Akodo Bushi School
* Bayushi Bushi School
* Shiba Bushi School


#### Characters with Peasant Professions

Characters with a profession have to buy their first ranks of Attack and Parry,
and do not receive the free ring raise to 3. However, they gain profession
abilities.

Starting characters with professions take one ability at character creation.
Characters with earned XP take one additional ability per 15 XP earned. Each
ability may be taken at most twice, except Priest abilities, which may only
be taken once.

Currently we only support Wave Man abilities.

See below for an explanation of abilities and how to take them.


#### Characters without School or Profession

You may also build a "generic" character that does not have a profession or a school.

In this case, you will have to pay for your first ranks of Attack and Parry, and you
will not gain profession abilities.


### Character Rings

Rings are required.

The Rings are:
* air
* earth
* fire
* water
* void

Allowed values are between 2 and 5.
A character with a school may set their school ring to 6.


### Character Skills

Skills are required.

The skills supported in the simulator are:
* attack
* double attack
* feint (although strategies to use it are lacking)
* parry

We plan to add support in the near future for:
* counterattack
* iaijutsu
* lunge

You may also put other valid L7R skills, but they are not
used in the simulator at this time.


### Character Abilities

Characters with peasant professions may take abilites, as
explained above.

Avaialble abilities are:
* crippled bonus
* damage penalty
* failed parry damage bonus
* initiative bonus
* missed attack bonus
* parry penalty
* rolled damage bonus
* weapon damage bonus
* wound check bonus
* wound check penalty

Explanation of the abilities:

**crippled bonus:** you may reroll tens on a single die when
crippled.

**damage penalty:** when someone is keeping at least one extra die
of damage from exceeding their attack roll TN, subtract 5 from the
damage.

**failed parry damage bonus**: when someone unsuccessfully tries to
parry an attack, you may roll 2 of the extra damage dice that you
would have rolled had they not attempted to parry.

**initiative bonus:** roll one extra unkept die on initiative.

**missed attack bonus:** when you make an attack roll that would
miss, raise it by 5. Any parry attempt against an attack that
would hit because of this ability automatically succeeds.

**parry penalty:** raise the TN of someone trying to parry one of
your attacks by 5.

**rolled damage bonus:** round your damage rolls up to the nearest
multiple of 5. If the roll is already a multiple of 5, then raise
it by 3.

**weapon damage bonus:** when using a weapon that deals less than
4k2 damage, add an extra rolled damage die to the weapon's base
damage, to a maximum of 4k2 base damage. Also, subtract 2 from your
armor damage reduction penalty.
(The damage reduction part of this ability is not yet supported,
since damage reduction is not implemented.)

**wound check bonus:** roll two extra unkept dice on wound checks.

**wound check penalty:** raise the TN of someone making a Wound
Check from damage you dealt to them by 5. If they fail, they take
Serious Wounds as if the TN had not been raised.


### Character Advantages

Characters may buy advantages at character creation time.
All of the advantages from the core rules are supported,
but the only advantages that have any mechanical effect at
this time are:
* Great Destiny
* Strength of the Earth


### Character Disadvantages

Characters may take disadvantages at character creation time.
All disadvantages from the core rules are supported,
but the only advantages that have any mechanical effect at
this time are:
* Permanent Wound


### Advice for Building a Character

Combat usually happens only once or twice per adventure, so a
character will need social and knowledge skills to be fun to play!
Sincerity and tact are essential for every character, and other
skills are important depending on what kind of things you want to
be good at.

You should absolutely buy Attack and Parry so your TN to be hit is
higher.
* 2 Attack, 3 Parry: enemies with 2 Fire will miss you half the
time, but enemies with 3 Fire will usually hit. High Fire enemies
have a good chance of getting extra kept dice of damage against you.
This costs 14 XP for samurai characters and 22 XP for peasants.
* 3 Attack, 4 Parry: enemies with 2 Fire usually miss you, and
enemies with 3 Fire miss you about half the time. This is the
cheapest way to survive most combats at low levels! Costs 28 XP
for samurai characters, 36 XP for peasants.
* 4 Attack, 5 Parry: unrealistic for low XP characters, but
important for high XP characters. Enemies have a hard time hitting
you with less than 4 Fire without using VP or abilities. Costs
46 XP for samurai characters, 54 XP for peasants.


After raising your attack and parry, you should think about raising
some of your Rings. It costs 60-75 XP to raise every ring to 3, so
until high XP levels, most characters have to leave a couple of rings
at 2. The question is what is important to you.


**Air**
Air is used for social rolls and parrying attacks. This ring is
important if you're playing a parry school, or if you care about
your character doing well at social skills such as lying, bragging,
intimidation, interrogation, or winning arguments.


**Earth**
Earth determines how many Serious Wounds you can take before you
are crippled and then dead. You will have to invest in Earth as you
gain XP and face more dangerous enemies. However, it is commonly a
dump stat for low and mid level characters.


**Fire**
Fire is used for attacking and damage, and also for sneaking. This
is the most important ring if you want to do a lot of damage in
combat.

Here is what you can expect from different Fire rings:
* 2 Fire: your attack roll is 20 less than half the time. You have
a hard time hitting enemies with as little as 3 Parry. If you hit,
you usually do 15-20 damage.
* 3 Fire: your attack roll is 25 about half the time, so you usually
hit enemies with 3 Parry or less, but enemies with 4 or 5 Parry are
still hard for you to hit. You usually get 15 to 23 damage.
* 4 Fire: your attack roll is 30 more than half the time, so you
usually hit any enemy. If you lunge or get a lucky attack roll, you
can get to three kept damage dice and do 25-35 damage, but your
usual attacks get 17-27 damage.
* 5 Fire: your usual attack roll is 35-50, so the question is no
longer whether you hit, but just how hard you hit! You often get
extra kept damage dice and do 30 to 38 damage.
* 6 Fire: only possible for samurai characters with Fire schools.
Your attack roll is 50 or higher more than half the time, and you
usually keep extra damage dice and do 35-45 damage.


**Water**
This powerful ring is used for knowledge skills and Wound Checks.
Characters with higher Water can take more hits before they take
a Serious Wound.

The rule for Wound Checks is that if you succeed, you may choose to
keep your Light Wounds, and your Wound Check TN will be higher on
the next hit, or you may take 1 Serious Wound and reset your Light
Wounds to zero. And if you fail, you take 1 Serious Wound
automatically, plus an additional Serious Wound for each increment
of 10 by which you missed the TN.

This rule means that characters should be making risky Wound Checks
where they are likely to fail by 9 or less, so that they can stretch
out their Serious Wounds.

With all that in mind, here is what you can expect from different
Water rings:
* 2 Water: you take at least 1 SW from every hit. You are in great
danger if your enemies get lucky damage rolls - you can easily take
2-3 SW from big hits.
* 3 Water: you usually succeed at Wound Checks against normal hits,
and you can consider keeping the LW from a low damage roll if you
can save VP for your next Wound Check. This only results in 2-3 SW
about 10% of the time. Strong enemies can still do 2-3 SW to you in
a single hit if they get a lucky damage roll and you get an average
or below average Wound Check roll.
* 4 Water: you can usually stretch out your LW and take 1 SW
every other hit. Sometimes this will result in 2 SW from the second
hit, but in that case you just break even, so it's a good risk.
Strong characters can still threaten multiple SW with a good damage
roll.
* 5 Water: similar to 4 Water, but you are usually able to take
just 1 SW even from a good damage roll by a strong character.
* 6 Water: you can take three hits from weak characters before you
take a Serious Wound, and if you have VP, you can consider keeping
LW from a hit by a strong character.


**Void**
Void determines the number of actions you can take each round. This
is crucially important for characters who want to be good at duels,
and also tends to be important for characters with Parry schools, if
they want to have enough actions to parry attacks and also throw
some attacks back at their enemies.


### Character Strategies

Strategies are used to determine character behavior. You may override
strategies to customize a character's behavior.

Strategies are the most important part of the simulator, and also the
most difficult to write.

You should be careful about overriding the strategies of a character
with a school or profession! Certain schools have a custom strategies
that take into account their special abilities. Overriding their
strategies may result in nerfing the character's school or profession
abilities.


#### Action Strategies

A character's action strategy determines whether to act when an action
is available.

Specify an action strategy like this:
```
strategies:
  action: NameOfStrategy
```

Available action strategies are:
* `AlwaysAttackActionStrategy`: always attack as soon as an action is available
* `HoldOneActionStrategy`: do not attack unless you have two available actions,
until Phase 10

The default action strategy is `HoldOneActionStrategy`.


#### Attack Strategies

Attack strategies determine how a character attacks.

Specify an attack strategy like this:
```
strategies:
  attack: NameOfStrategy
```

Available attack strategies are:
* `PlainAttackStrategy`: find the easiest character to hit, and use the attack skill to attack them.
Spend Void Points if it is likely the attack roll would result in keeping additional damage dice.
* `StingyPlainAttackStrategy`: like `PlainAttackStrategy`, but never spend VP.
* `UniversalAttackStrategy`: find the easiest character to hit. Try double attack first, then consider
a feint if out of VP, then fall back to a plain attack. Spend VP if probable to get extra kept damage dice.

The default attack strategy is `UniversalAttackStrategy`.


#### Parry Strategies

Parry strategies determine whether and how a character parries.

Specify a parry strategy like this:
```
strategies:
  parry: NameOfStrategy
```

Available parry strategies are:
* `AlwaysParryStrategy`: always parry an attack after it is rolled if it's a hit.
* `NeverParryStrategy`: never parry an attack.
* `ReluctantParryStrategy`: parry an attack if it's expected to deal more than 2 SW.
Try to shirk parrying for a friend unless you are the only person who can do it.

The default parry strategy is `ReluctantParryStrategy`.


#### Light Wounds Strategies

Light wounds strategies determine whether to keep light wound after a successful wound check.

Specify a light wounds strategy like this:
```
strategies:
  light_wounds: NameOfStrategy
```

Available light wounds strategies are:
* `AlwaysKeepLightWoundsStrategy`: always keep light wounds after a successful wound check.
* `KeepLightWoundsStrategy`: keep light wounds if the average damage rolls made by the enemy
group would make the next wound check dangerous (chance of taking more than 2 SW on the next
wound check is greater than 50%).
* `NeverKeepLightWoundsStrategy`: always take a Serious Wound after a successful wound check.

The default light wounds strategy is `KeepLightWoundsStrategy`.


### Wound Check Strategies

Wound check strategies determine how many Void Points to spend on a wound check.

Specify a wound check strategy like this:
```
strategies:
  wound_check: NameOfStrategy
```

Available wound check strategies are:
* `StingyWoundCheckStrategy`: never spend Void Points on wound checks.
* `WoundCheckStrategy`: if this character's average wound check roll would result in taking
more than 1 Serious Wound, spend as many VP as possible until the expected number of
Serious Wounds is reduced to 1.

The default wound check strategy is `WoundCheckStrategy`.


# Output

The simulator outputs a CSV file in the output directory (set by the `-o` flag) that
gives statistics captured from each trial run. The data in this file is used to
generate a summary report that is printed to the command line after a run.

The report gives the test group's win rate and some stats about the test and control
group. It gives the same stats again "given test group victory" and "given control
group victory", which means that the second and third reports are statistics for only
the trials where the test group won or the control group won. This is intended to
help determine what kinds of variables reinforce or undercut a certain strategy. For
example, certain characters, schools, or strategies may be seriously undercut by
a certain kind of unlucky roll.

